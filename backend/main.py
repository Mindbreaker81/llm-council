"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple
import uuid
import json
import asyncio
import logging

from . import storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings, get_council_config
from .config import (
    COUNCIL_TYPE_CUSTOM,
    COUNCIL_TYPE_PREMIUM,
    VALID_COUNCIL_TYPES,
    OPENROUTER_API_KEY,
    ALLOWED_ORIGINS_ENV,
    ALLOW_ORIGIN_REGEX_ENV,
)
from .model_catalog import (
    filter_models,
    find_model,
    get_models,
    normalize_model,
    validate_custom_council_from_catalog,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="LLM Council API")
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def validate_api_key():
    """Fail fast if OpenRouter API key is not configured."""
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is not configured. Set it in .env and restart.")
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    logger.info("OPENROUTER_API_KEY is configured")


# CORS configuration with environment variable support
# Default origins include localhost for local development
# Set ALLOWED_ORIGINS env var to override (comma-separated list)
default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

if ALLOWED_ORIGINS_ENV:
    # Split by comma and add to default origins
    additional_origins = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",") if origin.strip()]
    default_origins.extend(additional_origins)

# Remove duplicates while preserving order
seen = set()
allowed_origins = []
for origin in default_origins:
    if origin not in seen:
        seen.add(origin)
        allowed_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=ALLOW_ORIGIN_REGEX_ENV or None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    council_type: str = Field(
        default=COUNCIL_TYPE_PREMIUM,
        description="Type of council: premium, economic, free, or custom"
    )


class CustomCouncilRequest(BaseModel):
    """Custom council model selection."""
    models: List[str]
    chairman_model: Optional[str] = None


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    council_type: str = Field(
        default=COUNCIL_TYPE_PREMIUM,
        description="Type of council: premium, economic, free, or custom"
    )
    custom_council: Optional[CustomCouncilRequest] = None


class ValidateCouncilRequest(BaseModel):
    """Request to validate custom council model choices."""
    models: List[str]
    chairman_model: Optional[str] = None


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int
    council_type: str = COUNCIL_TYPE_PREMIUM


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]
    council_type: str = COUNCIL_TYPE_PREMIUM


class CouncilResponse(BaseModel):
    """Complete council response payload."""
    stage1: List[Dict[str, Any]]
    stage2: List[Dict[str, Any]]
    stage3: Dict[str, Any]
    metadata: Dict[str, Any]


def normalize_council_type(council_type: Optional[str]) -> Optional[str]:
    """Return a supported council type or None for invalid values."""
    if council_type in VALID_COUNCIL_TYPES:
        return council_type
    return None


async def prepare_custom_council(request: SendMessageRequest) -> Optional[Dict[str, Any]]:
    """Validate and normalize a custom council request for execution and storage."""
    if normalize_council_type(request.council_type) != COUNCIL_TYPE_CUSTOM:
        return None
    if request.custom_council is None:
        raise HTTPException(status_code=400, detail="custom_council is required for custom council type")

    catalog = await get_models()
    validation = validate_custom_council_from_catalog(
        catalog,
        request.custom_council.models,
        request.custom_council.chairman_model,
    )
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={
            "message": "Invalid custom council",
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        })

    custom_council = {
        "models": validation["model_ids"],
        "chairman_model": validation["chairman_model_id"],
        "chairman_context_length": (
            validation["chairman_model"] or {}
        ).get("context_length"),
    }
    return {
        "custom_council": custom_council,
        "model_metadata": validation["model_metadata"],
        "warnings": validation["warnings"],
    }


async def _resolve_message_request(
    conversation_id: str,
    request: SendMessageRequest,
) -> Tuple[Dict[str, Any], str, Optional[Dict[str, Any]], bool]:
    """Validate conversation and council type, and prepare a custom council if needed."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    council_type = normalize_council_type(request.council_type)
    if council_type is None:
        raise HTTPException(status_code=400, detail=f"Invalid council_type: {request.council_type}")

    custom_context = await prepare_custom_council(request)
    is_first_message = len(conversation["messages"]) == 0
    return conversation, council_type, custom_context, is_first_message


def _build_council_metadata(
    council_type: str,
    label_to_model: Optional[Dict[str, str]] = None,
    aggregate_rankings: Optional[List[Dict[str, Any]]] = None,
    custom_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the metadata dict shared by responses and stored messages."""
    metadata: Dict[str, Any] = {"council_type": council_type}
    if label_to_model:
        metadata["label_to_model"] = label_to_model
    if aggregate_rankings:
        metadata["aggregate_rankings"] = aggregate_rankings
    if custom_context:
        metadata["custom_council"] = custom_context["custom_council"]
        metadata["model_metadata"] = custom_context["model_metadata"]
        metadata["warnings"] = custom_context["warnings"]
    return metadata


def _persist_council_result(
    conversation_id: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    stage3_result: Dict[str, Any],
    council_type: str,
    metadata: Dict[str, Any],
    custom_context: Optional[Dict[str, Any]],
) -> None:
    """Persist the full council response as an assistant message."""
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result,
        council_type=council_type,
        custom_council=custom_context["custom_council"] if custom_context else None,
        model_metadata=custom_context["model_metadata"] if custom_context else None,
    )


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/councils")
async def list_councils():
    """List built-in council presets and their active models."""
    presets = []
    for council_type in sorted(VALID_COUNCIL_TYPES):
        if council_type == COUNCIL_TYPE_CUSTOM:
            continue
        models, chairman_model = get_council_config(council_type)
        presets.append({
            "type": council_type,
            "models": models,
            "chairman_model": chairman_model,
        })
    return {"presets": presets}


@app.get("/api/models")
async def list_models(
    free_only: bool = False,
    text_only: bool = True,
    supports: Optional[str] = None,
    min_context: Optional[int] = None,
    sort: str = "pricing-low-to-high",
    q: Optional[str] = None,
    refresh: bool = False,
):
    """List OpenRouter models for custom council selection."""
    support_filters = [item.strip() for item in supports.split(",")] if supports else []
    models = await get_models(refresh=refresh)
    filtered = filter_models(
        models,
        free_only=free_only,
        text_only=text_only,
        supports=support_filters,
        min_context=min_context,
        query=q,
        sort=sort,
    )
    return {
        "count": len(filtered),
        "models": [normalize_model(model) for model in filtered],
    }


@app.get("/api/models/detail")
async def get_model_detail(model_id: str = Query(..., description="OpenRouter model id")):
    """Get one OpenRouter model by id."""
    models = await get_models()
    model = find_model(models, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return normalize_model(model)


@app.post("/api/councils/validate")
async def validate_custom_council(request: ValidateCouncilRequest):
    """Validate a custom council selection."""
    models = await get_models()
    return validate_custom_council_from_catalog(
        models,
        request.models,
        request.chairman_model,
    )


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    council_type = normalize_council_type(request.council_type)
    if council_type is None:
        raise HTTPException(status_code=400, detail=f"Invalid council_type: {request.council_type}")

    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id, council_type=council_type)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    success = storage.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "id": conversation_id}


@app.post("/api/conversations/{conversation_id}/message", response_model=CouncilResponse)
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    _, council_type, custom_context, is_first_message = await _resolve_message_request(
        conversation_id, request
    )

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    logger.info("Running council response with type %s", council_type)
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        council_type=council_type,
        custom_council=custom_context["custom_council"] if custom_context else None,
    )

    # Enrich metadata with custom council context
    metadata = _build_council_metadata(
        council_type,
        label_to_model=metadata.get("label_to_model"),
        aggregate_rankings=metadata.get("aggregate_rankings"),
        custom_context=custom_context,
    )

    # Add assistant message with all stages (include council_type for display in chat and PDF)
    _persist_council_result(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result,
        council_type,
        metadata,
        custom_context,
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata,
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    _, council_type, custom_context, is_first_message = await _resolve_message_request(
        conversation_id, request
    )

    async def event_generator():
        user_message_saved = False
        assistant_message_saved = False
        stage1_results = []
        stage2_results = []
        stage3_result = None
        metadata = _build_council_metadata(council_type, custom_context=custom_context)

        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)
            user_message_saved = True

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Get council configuration
            logger.info("Running streaming council response with type %s", council_type)
            custom_council = custom_context["custom_council"] if custom_context else None
            use_fallback = council_type != COUNCIL_TYPE_CUSTOM
            council_models, chairman_model = get_council_config(council_type, custom_council)

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(
                request.content,
                council_models,
                use_fallback=use_fallback
            )
            logger.info("Stage 1 completed with %s results", len(stage1_results))
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results, 'council_type': council_type})}\n\n"

            # Stage 2: Collect rankings (only if Stage 1 has results)
            if not stage1_results:
                logger.info("Skipping Stage 2 because Stage 1 returned no results")
                stage2_results = []
                label_to_model = {}
                aggregate_rankings = []
            else:
                yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
                stage2_results, label_to_model = await stage2_collect_rankings(
                    request.content,
                    stage1_results,
                    council_models,
                    use_fallback=use_fallback
                )
                aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
                metadata = _build_council_metadata(
                    council_type,
                    label_to_model=label_to_model,
                    aggregate_rankings=aggregate_rankings,
                    custom_context=custom_context,
                )
                yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': metadata})}\n\n"

            # Stage 3: Synthesize final answer (only if we have results)
            if not stage1_results:
                stage3_result = {
                    "model": chairman_model,
                    "response": "Error: No models responded successfully. Please check your API key and model availability, or try a different council type."
                }
                yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result, 'council_type': council_type})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
                stage3_result = await stage3_synthesize_final(
                    request.content,
                    stage1_results,
                    stage2_results,
                    chairman_model,
                    council_type,
                    custom_council.get("chairman_context_length") if custom_council else None
                )
                yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result, 'council_type': council_type})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            _persist_council_result(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result,
                council_type,
                metadata,
                custom_context,
            )
            assistant_message_saved = True

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            logger.exception("Streaming council response failed")
            if user_message_saved and not assistant_message_saved:
                error_stage3 = {
                    "model": "error",
                    "response": f"Error: {str(e)}"
                }
                try:
                    storage.add_assistant_message(
                        conversation_id,
                        stage1_results,
                        stage2_results,
                        stage3_result or error_stage3,
                        council_type=council_type,
                        custom_council=custom_context["custom_council"] if custom_context else None,
                        model_metadata=custom_context["model_metadata"] if custom_context else None,
                    )
                except Exception:
                    logger.exception("Failed to persist streaming error response")
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/health")
async def health_check():
    """Return a simple health status for monitoring and load balancers."""
    return {"status": "ok", "version": "2.5.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
