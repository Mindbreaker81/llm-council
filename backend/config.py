"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council type constants
COUNCIL_TYPE_PREMIUM = "premium"
COUNCIL_TYPE_ECONOMIC = "economic"
COUNCIL_TYPE_FREE = "free"
COUNCIL_TYPE_CUSTOM = "custom"
VALID_COUNCIL_TYPES = {
    COUNCIL_TYPE_PREMIUM,
    COUNCIL_TYPE_ECONOMIC,
    COUNCIL_TYPE_FREE,
    COUNCIL_TYPE_CUSTOM,
}

# Premium Council members - list of OpenRouter model identifiers
COUNCIL_MODELS_PREMIUM = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-opus-4.5",
    "x-ai/grok-4",
]

# Premium Chairman model - synthesizes final response
CHAIRMAN_MODEL_PREMIUM = "google/gemini-3-pro-preview"

# Economic Council members - list of OpenRouter model identifiers
COUNCIL_MODELS_ECONOMIC = [
    "qwen/qwen3-235b-a22b-thinking-2507",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-r1-0528-qwen3-8b",
    "nousresearch/hermes-4-70b",
]

# Economic Chairman model - synthesizes final response
CHAIRMAN_MODEL_ECONOMIC = "deepseek/deepseek-v3.1-terminus"

# Free Council members - list of OpenRouter model identifiers
# Note: Some free models may not be available, fallback to paid versions is automatic
COUNCIL_MODELS_FREE = [
    "mistralai/mistral-small-24b-instruct-2501:free",  # Falls back to paid version if unavailable
    "google/gemini-2.5-flash:free",  # Free model, falls back to paid if unavailable
    "z-ai/glm-4.5-air:free",  # Falls back to paid version if unavailable
    "deepseek/deepseek-r1-distill-qwen-32b",  # Already free, no :free suffix needed
]

# Free Chairman model - synthesizes final response
CHAIRMAN_MODEL_FREE = "deepseek/deepseek-r1-distill-llama-70b:free"  # Falls back to paid version if unavailable

# Fallback mapping: free models -> paid versions for automatic fallback
MODEL_FALLBACK_MAP = {
    "mistralai/mistral-small-24b-instruct-2501:free": "mistralai/mistral-small-24b-instruct-2501",
    "google/gemini-2.5-flash:free": "google/gemini-2.5-flash",  # Fallback to paid version
    "z-ai/glm-4.5-air:free": "z-ai/glm-4.5-air",
    "deepseek/deepseek-r1-distill-llama-70b:free": "deepseek/deepseek-r1-distill-llama-70b",
    # Note: xai/grok-4-fast:free and xai/grok-4-fast are not available, removed from config
}

# Legacy aliases for backward compatibility
COUNCIL_MODELS = COUNCIL_MODELS_PREMIUM
CHAIRMAN_MODEL = CHAIRMAN_MODEL_PREMIUM

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model used for automatic title generation (fast and cheap)
TITLE_GENERATION_MODEL = os.getenv("TITLE_GENERATION_MODEL", "google/gemini-2.5-flash")

# CORS security
# Comma-separated list of allowed origins; use this to lock down remote access.
ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS", "")
# Default regex for local development networks. Set to empty to disable.
ALLOW_ORIGIN_REGEX_ENV = os.getenv(
    "ALLOW_ORIGIN_REGEX",
    r"https?://("
    r"localhost|127\.0\.0\.1|0\.0\.0\.0|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?",
)

# Cost guardrail for custom councils (USD)
MAX_CUSTOM_COUNCIL_COST_USD = float(os.getenv("MAX_CUSTOM_COUNCIL_COST_USD", "5.0"))

# Project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data directory for conversation storage (absolute, so cwd does not matter)
DATA_DIR = os.path.join(BASE_DIR, "data", "conversations")
