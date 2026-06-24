"""JSON-based storage for conversations."""

import json
import os
import threading
import tempfile
from datetime import datetime
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR, COUNCIL_TYPE_PREMIUM

_locks_guard = threading.Lock()
_conversation_locks: Dict[str, threading.Lock] = {}


def ensure_data_dir():
    """Ensure the data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


@contextmanager
def conversation_lock(conversation_id: str):
    """Serialize read-modify-write operations for one conversation file."""
    with _locks_guard:
        lock = _conversation_locks.setdefault(conversation_id, threading.Lock())
    with lock:
        yield


def get_conversation_path(conversation_id: str) -> str:
    """Get the file path for a conversation."""
    return os.path.join(DATA_DIR, f"{conversation_id}.json")


def write_conversation_atomic(conversation: Dict[str, Any]):
    """Write a conversation JSON file atomically."""
    ensure_data_dir()

    path = get_conversation_path(conversation['id'])
    directory = os.path.dirname(path)
    fd, temp_path = tempfile.mkstemp(
        prefix=f".{conversation['id']}.",
        suffix=".tmp",
        dir=directory,
        text=True
    )
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(conversation, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise


def create_conversation(conversation_id: str, council_type: str = COUNCIL_TYPE_PREMIUM) -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        conversation_id: Unique identifier for the conversation
        council_type: Type of council to use ("premium" or "economic")

    Returns:
        New conversation dict
    """
    ensure_data_dir()

    conversation = {
        "id": conversation_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": "New Conversation",
        "messages": [],
        "council_type": council_type
    }

    with conversation_lock(conversation_id):
        write_conversation_atomic(conversation)

    return conversation


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation dict or None if not found
    """
    path = get_conversation_path(conversation_id)

    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        return json.load(f)


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to storage.

    Args:
        conversation: Conversation dict to save
    """
    with conversation_lock(conversation['id']):
        write_conversation_atomic(conversation)


def list_conversations() -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).

    Returns:
        List of conversation metadata dicts
    """
    ensure_data_dir()

    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                # Return metadata only
                conversations.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "title": data.get("title", "New Conversation"),
                    "message_count": len(data["messages"]),
                    "council_type": data.get("council_type", "premium")
                })

    # Sort by creation time, newest first
    conversations.sort(key=lambda x: x["created_at"], reverse=True)

    return conversations


def add_user_message(conversation_id: str, content: str):
    """
    Add a user message to a conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message content
    """
    with conversation_lock(conversation_id):
        conversation = get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation["messages"].append({
            "role": "user",
            "content": content
        })

        write_conversation_atomic(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    council_type: Optional[str] = None,
    custom_council: Optional[Dict[str, Any]] = None,
    model_metadata: Optional[Dict[str, Any]] = None
):
    """
    Add an assistant message with all 3 stages to a conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
        council_type: Type of council used for this message
        custom_council: Custom council model selection used for this message
        model_metadata: Snapshot of model metadata at send time
    """
    with conversation_lock(conversation_id):
        conversation = get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        message = {
            "role": "assistant",
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3
        }
        
        if council_type:
            message["council_type"] = council_type
        if custom_council:
            message["custom_council"] = custom_council
        if model_metadata:
            message["model_metadata"] = model_metadata

        conversation["messages"].append(message)

        write_conversation_atomic(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    with conversation_lock(conversation_id):
        conversation = get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation["title"] = title
        write_conversation_atomic(conversation)


def delete_conversation(conversation_id: str) -> bool:
    """
    Delete a conversation.

    Args:
        conversation_id: Conversation identifier

    Returns:
        True if deleted, False if not found
    """
    path = get_conversation_path(conversation_id)
    with conversation_lock(conversation_id):
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
