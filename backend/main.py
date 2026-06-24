"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio
import logging
import os

from . import storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings, get_council_config
from .config import COUNCIL_TYPE_PREMIUM, VALID_COUNCIL_TYPES
from .model_catalog import (
    filter_models,
    find_model,
    get_models,
    normalize_model,
    validate_custom_council_from_catalog,
)

app = FastAPI(title="LLM Council API")
logger = logging.getLogger(__name__)

# CORS configuration with environment variable support
# Default origins include localhost for local development
# Set ALLOWED_ORIGINS env var to override (comma-separated list)
default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    # Tailscale support
    "http://100.126.204.86:5174",
    "http://quimserver.tail19aa19.ts.net:5174",
    "https://quimserver.tail19aa19.ts.net:5174",
]

# Get additional origins from environment variable
env_origins = os.getenv("ALLOWED_ORIGINS", "")
if env_origins:
    # Split by comma and add to default origins
    additional_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    council_type: str = Field(
        default=COUNCIL_TYPE_PREMIUM,
        description="Type of council: premium, economic, or free"
    )


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    council_type: str = Field(
        default=COUNCIL_TYPE_PREMIUM,
        description="Type of council: premium, economic, or free"
    )


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


def normalize_council_type(council_type: str) -> str:
    """Return a supported council type, defaulting to premium for legacy clients."""
    if council_type in VALID_COUNCIL_TYPES:
        return council_type
    return COUNCIL_TYPE_PREMIUM


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


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
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(
        conversation_id,
        council_type=normalize_council_type(request.council_type)
    )
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
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    council_type = normalize_council_type(request.council_type)
    
    # Run the 3-stage council process
    logger.info("Running council response with type %s", council_type)
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        council_type=council_type
    )

    # Add assistant message with all stages (include council_type for display in chat and PDF)
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result,
        council_type=council_type
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    council_type = normalize_council_type(request.council_type)

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Get council configuration
            logger.info("Running streaming council response with type %s", council_type)
            council_models, chairman_model = get_council_config(council_type)

            # Stage 1: Collect responses (include council_type so frontend has it even when stage2 is skipped)
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content, council_models)
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
                stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results, council_models)
                aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
                yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings, 'council_type': council_type}})}\n\n"

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
                    council_type
                )
                yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result, 'council_type': council_type})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result,
                council_type=council_type
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            logger.exception("Streaming council response failed")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
