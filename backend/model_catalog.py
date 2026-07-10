"""OpenRouter model catalog helpers."""

import time
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Sequence

import httpx

from .config import OPENROUTER_API_KEY, MAX_CUSTOM_COUNCIL_COST_USD

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_USER_MODELS_URL = "https://openrouter.ai/api/v1/models/user"
CATALOG_TTL_SECONDS = 15 * 60
MIN_CUSTOM_MODELS = 2
MAX_CUSTOM_MODELS = 8

_catalog_cache: Dict[str, Any] = {
    "fetched_at": 0.0,
    "models": [],
}


def parse_price(value: Any) -> Decimal:
    """Parse OpenRouter string pricing into Decimal."""
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def is_free_model(model: Dict[str, Any]) -> bool:
    """Return True when prompt, completion, and request pricing are all zero."""
    pricing = model.get("pricing") or {}
    return (
        parse_price(pricing.get("prompt")) == 0
        and parse_price(pricing.get("completion")) == 0
        and parse_price(pricing.get("request")) == 0
    )


def supports_text_io(model: Dict[str, Any]) -> bool:
    """Return True when model accepts text and returns text."""
    architecture = model.get("architecture") or {}
    input_modalities = architecture.get("input_modalities") or []
    output_modalities = architecture.get("output_modalities") or []
    return "text" in input_modalities and "text" in output_modalities


def get_context_length(model: Dict[str, Any]) -> Optional[int]:
    """Extract context length from the highest-signal catalog fields."""
    top_provider = model.get("top_provider") or {}
    value = top_provider.get("context_length") or model.get("context_length")
    return value if isinstance(value, int) else None


def price_per_million(value: Any) -> str:
    """Convert per-token pricing to a display-friendly per-1M-token string."""
    return str(parse_price(value) * Decimal("1000000"))


def normalize_model(model: Dict[str, Any]) -> Dict[str, Any]:
    """Return the subset of model metadata used by the app."""
    pricing = model.get("pricing") or {}
    top_provider = model.get("top_provider") or {}
    architecture = model.get("architecture") or {}

    return {
        "id": model.get("id"),
        "name": model.get("name") or model.get("id"),
        "description": model.get("description"),
        "pricing": pricing,
        "price_per_million": {
            "prompt": price_per_million(pricing.get("prompt")),
            "completion": price_per_million(pricing.get("completion")),
            "request": price_per_million(pricing.get("request")),
        },
        "free": is_free_model(model),
        "context_length": get_context_length(model),
        "max_completion_tokens": top_provider.get("max_completion_tokens"),
        "input_modalities": architecture.get("input_modalities") or [],
        "output_modalities": architecture.get("output_modalities") or [],
        "supported_parameters": model.get("supported_parameters") or [],
        "dynamic_router": model.get("id") == "openrouter/free",
    }


async def fetch_models_from_openrouter() -> List[Dict[str, Any]]:
    """Fetch the model catalog, preferring the key-scoped endpoint."""
    headers = {}
    if OPENROUTER_API_KEY:
        headers["Authorization"] = f"Bearer {OPENROUTER_API_KEY}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        if OPENROUTER_API_KEY:
            try:
                response = await client.get(OPENROUTER_USER_MODELS_URL, headers=headers)
                response.raise_for_status()
                return response.json().get("data", [])
            except httpx.HTTPError:
                pass

        response = await client.get(OPENROUTER_MODELS_URL)
        response.raise_for_status()
        return response.json().get("data", [])


async def get_models(refresh: bool = False) -> List[Dict[str, Any]]:
    """Get cached OpenRouter models, refreshing after TTL."""
    now = time.monotonic()
    if (
        not refresh
        and _catalog_cache["models"]
        and now - _catalog_cache["fetched_at"] < CATALOG_TTL_SECONDS
    ):
        return _catalog_cache["models"]

    models = await fetch_models_from_openrouter()
    _catalog_cache["models"] = models
    _catalog_cache["fetched_at"] = now
    return models


def filter_models(
    models: Sequence[Dict[str, Any]],
    *,
    free_only: bool = False,
    text_only: bool = True,
    supports: Optional[Sequence[str]] = None,
    min_context: Optional[int] = None,
    query: Optional[str] = None,
    sort: str = "pricing-low-to-high",
) -> List[Dict[str, Any]]:
    """Filter and sort models for the frontend selector."""
    supports = [item for item in (supports or []) if item]
    query_lower = query.lower() if query else None
    filtered = []

    for model in models:
        if text_only and not supports_text_io(model):
            continue
        if free_only and not is_free_model(model):
            continue
        if supports and not set(supports).issubset(set(model.get("supported_parameters") or [])):
            continue
        context_length = get_context_length(model) or 0
        if min_context is not None and context_length < min_context:
            continue
        if query_lower:
            haystack = f"{model.get('id', '')} {model.get('name', '')}".lower()
            if query_lower not in haystack:
                continue
        filtered.append(model)

    if sort == "context-high-to-low":
        filtered.sort(key=lambda item: get_context_length(item) or 0, reverse=True)
    elif sort == "name":
        filtered.sort(key=lambda item: item.get("name") or item.get("id") or "")
    else:
        filtered.sort(
            key=lambda item: (
                parse_price((item.get("pricing") or {}).get("prompt")),
                parse_price((item.get("pricing") or {}).get("completion")),
                item.get("name") or item.get("id") or "",
            )
        )

    return filtered


def find_model(models: Sequence[Dict[str, Any]], model_id: str) -> Optional[Dict[str, Any]]:
    """Find one model by id."""
    return next((model for model in models if model.get("id") == model_id), None)


def _estimate_call_cost(
    model: Dict[str, Any],
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    """Return the estimated cost for one prompt+completion call."""
    pricing = model.get("pricing") or {}
    return (
        parse_price(pricing.get("prompt")) * input_tokens
        + parse_price(pricing.get("completion")) * output_tokens
        + parse_price(pricing.get("request"))
    )


def estimate_council_cost(
    selected_models: Sequence[Dict[str, Any]],
    chairman_model: Dict[str, Any],
    input_tokens: int = 1000,
    output_tokens: int = 1000,
) -> Dict[str, Any]:
    """Estimate rough 2N+1 council cost for display guardrails.

    Stage 1 and Stage 2 each call every selected model once. Stage 3 calls the
    chairman once. If the chairman is also a selected model, it is counted for
    all three calls as expected.
    """
    total = Decimal("0")
    calls = []

    for model in selected_models:
        call_cost = _estimate_call_cost(model, input_tokens, output_tokens)
        total += call_cost
        calls.append({
            "model": model.get("id"),
            "stage": "stage1",
            "estimated_cost_usd": str(call_cost),
        })

    for model in selected_models:
        call_cost = _estimate_call_cost(model, input_tokens, output_tokens)
        total += call_cost
        calls.append({
            "model": model.get("id"),
            "stage": "stage2",
            "estimated_cost_usd": str(call_cost),
        })

    if chairman_model:
        call_cost = _estimate_call_cost(chairman_model, input_tokens, output_tokens)
        total += call_cost
        calls.append({
            "model": chairman_model.get("id"),
            "stage": "stage3",
            "estimated_cost_usd": str(call_cost),
        })

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_total_usd": str(total),
        "calls_count": len(calls),
        "calls": calls,
    }


def snapshot_models(models: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build reproducible metadata for saved custom council messages."""
    return {
        model["id"]: {
            "name": model.get("name") or model.get("id"),
            "pricing": model.get("pricing") or {},
            "context_length": get_context_length(model),
        }
        for model in models
        if model.get("id")
    }


def validate_custom_council_from_catalog(
    catalog: Sequence[Dict[str, Any]],
    model_ids: Sequence[str],
    chairman_model_id: Optional[str],
) -> Dict[str, Any]:
    """Validate a custom council selection against a catalog snapshot."""
    errors = []
    warnings = []
    unique_model_ids = list(dict.fromkeys(model_ids))

    if len(unique_model_ids) < MIN_CUSTOM_MODELS:
        errors.append(f"Select at least {MIN_CUSTOM_MODELS} council models.")
    if len(unique_model_ids) > MAX_CUSTOM_MODELS:
        errors.append(f"Select at most {MAX_CUSTOM_MODELS} council models.")

    selected_models = []
    for model_id in unique_model_ids:
        model = find_model(catalog, model_id)
        if model is None:
            errors.append(f"Unknown model: {model_id}")
            continue
        if not supports_text_io(model):
            errors.append(f"Model does not support text input and output: {model_id}")
            continue
        selected_models.append(model)

    effective_chairman_id = chairman_model_id or (unique_model_ids[0] if unique_model_ids else None)
    chairman_model = find_model(catalog, effective_chairman_id) if effective_chairman_id else None
    if chairman_model is None:
        errors.append("Select a valid chairman model.")
    elif not supports_text_io(chairman_model):
        errors.append(f"Chairman model does not support text input and output: {effective_chairman_id}")

    if any(model.get("id") == "openrouter/free" for model in selected_models):
        warnings.append("openrouter/free is a dynamic router; results may be less reproducible.")

    chairman_context = get_context_length(chairman_model or {})
    if chairman_context is not None and chairman_context < 32000:
        warnings.append("The selected chairman has less than 32k context; long councils may need summarization.")

    snapshot_source = [*selected_models]
    if chairman_model and chairman_model not in snapshot_source:
        snapshot_source.append(chairman_model)

    estimated_cost = estimate_council_cost(selected_models, chairman_model) if chairman_model else None
    if estimated_cost and parse_price(estimated_cost["estimated_total_usd"]) > Decimal(str(MAX_CUSTOM_COUNCIL_COST_USD)):
        errors.append(
            f"Estimated cost ${estimated_cost['estimated_total_usd']} exceeds the "
            f"maximum allowed ${MAX_CUSTOM_COUNCIL_COST_USD:.2f}. Reduce the number of models or choose cheaper ones."
        )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "models": [normalize_model(model) for model in selected_models],
        "chairman_model": normalize_model(chairman_model) if chairman_model else None,
        "model_ids": [model["id"] for model in selected_models],
        "chairman_model_id": chairman_model.get("id") if chairman_model else effective_chairman_id,
        "model_metadata": snapshot_models(snapshot_source),
        "estimated_cost": estimated_cost,
    }
