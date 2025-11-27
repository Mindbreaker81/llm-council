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

# Data directory for conversation storage
DATA_DIR = "data/conversations"
