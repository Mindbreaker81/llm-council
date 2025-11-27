"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid
import json
import asyncio

from . import storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings, get_council_config
from .config import COUNCIL_TYPE_PREMIUM, COUNCIL_TYPE_ECONOMIC, COUNCIL_TYPE_FREE

app = FastAPI(title="LLM Council API")

# CORS configuration with environment variable support
# Default origins include localhost for local development
# Set ALLOWED_ORIGINS env var to override (comma-separated list)
import os
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


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id, council_type=request.council_type)
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


@app.post("/api/conversations/{conversation_id}/message")
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

    # Validate council_type
    valid_types = [COUNCIL_TYPE_PREMIUM, COUNCIL_TYPE_ECONOMIC, COUNCIL_TYPE_FREE]
    if request.council_type not in valid_types:
        request.council_type = COUNCIL_TYPE_PREMIUM  # Fallback to premium if invalid
    
    # Run the 3-stage council process
    print(f"DEBUG: send_message - Received council_type: {request.council_type}")
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        council_type=request.council_type
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
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

    # Validate council_type
    valid_types = [COUNCIL_TYPE_PREMIUM, COUNCIL_TYPE_ECONOMIC, COUNCIL_TYPE_FREE]
    if request.council_type not in valid_types:
        request.council_type = COUNCIL_TYPE_PREMIUM  # Fallback to premium if invalid

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
            print(f"DEBUG: Received council_type: {request.council_type}")
            council_models, chairman_model = get_council_config(request.council_type)
            print(f"DEBUG: Using council models: {council_models}")
            print(f"DEBUG: Using chairman model: {chairman_model}")

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content, council_models)
            print(f"DEBUG: Stage 1 completed with {len(stage1_results)} results")
            if stage1_results:
                print(f"DEBUG: Stage 1 first result: {stage1_results[0]}")
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings (only if Stage 1 has results)
            if not stage1_results:
                print(f"DEBUG: Skipping Stage 2 - Stage 1 has 0 results")
                stage2_results = []
                label_to_model = {}
                aggregate_rankings = []
            else:
                yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
                stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results, council_models)
                aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
                yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings, 'council_type': request.council_type}})}\n\n"

            # Stage 3: Synthesize final answer (only if we have results)
            if not stage1_results:
                stage3_result = {
                    "model": chairman_model,
                    "response": "Error: No models responded successfully. Please check your API key and model availability, or try a different council type."
                }
            else:
                yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
                stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results, chairman_model)
                yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

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
                council_type=request.council_type
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
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
