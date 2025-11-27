"""OpenRouter API client for making LLM requests."""

import httpx
import re
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL, MODEL_FALLBACK_MAP


def extract_final_content(response_text: str) -> str:
    """
    Extract final content from response that may contain reasoning tokens.
    
    Models like DeepSeek R1 emit reasoning tokens in <think> tags or similar.
    This function extracts only the final answer, removing reasoning blocks.
    
    Args:
        response_text: Raw response text that may contain reasoning tokens
        
    Returns:
        Final content without reasoning tokens
    """
    if not response_text:
        return ""
    
    text = response_text
    
    # Remove <think>...</think> blocks (common in reasoning models like DeepSeek R1)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove <think>...</think> blocks (common in reasoning models)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove <reasoning>...</reasoning> tags if present
    text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    text = text.strip()
    
    # If after cleaning we have nothing, return original (might not have reasoning tokens)
    if not text:
        return response_text
    
    return text


def get_fallback_model(model_id: str) -> Optional[str]:
    """
    Get fallback model (paid version) for a free model.
    
    Args:
        model_id: Model identifier (may include :free)
        
    Returns:
        Fallback model identifier or None if no fallback available
    """
    return MODEL_FALLBACK_MAP.get(model_id)


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    extract_final_content_flag: bool = False,
    use_fallback: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API with fallback support.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o" or "model:free")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds
        extract_final_content_flag: If True, extract only final content (remove reasoning tokens)
        use_fallback: If True, try fallback model if free model fails

    Returns:
        Response dict with 'content', 'original_content', and optional 'reasoning_details', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            original_content = message.get('content', '')
            reasoning_details = message.get('reasoning_details')
            
            # Extract final content if requested
            # When extract_final_content_flag=False, we still want to return the original content
            # as both content and original_content for consistency
            if extract_final_content_flag and original_content:
                final_content = extract_final_content(original_content)
            else:
                final_content = original_content

            result = {
                'content': final_content if final_content else original_content,
                'original_content': original_content,
                'reasoning_details': reasoning_details
            }
            
            # Debug log
            content_length = len(original_content) if original_content else 0
            final_length = len(final_content) if final_content else 0
            print(f"DEBUG: {model} - original_content length: {content_length}, final_content length: {final_length}")
            if original_content:
                print(f"DEBUG: {model} returned content (preview: {original_content[:50]}...)")
            else:
                print(f"DEBUG: {model} returned empty content")
            
            return result

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200] if e.response.text else 'No response body'}"
        print(f"Error querying model {model}: {error_msg}")
        
        # Try fallback if enabled and model is a free model
        if use_fallback:
            fallback_model = get_fallback_model(model)
            if fallback_model:
                print(f"Attempting fallback to {fallback_model}")
                return await query_model(
                    fallback_model,
                    messages,
                    timeout,
                    extract_final_content_flag,
                    use_fallback=False  # Don't recurse on fallback
                )
        
        return None
    except Exception as e:
        error_msg = str(e)
        print(f"Error querying model {model}: {error_msg}")
        
        # Try fallback if enabled and model is a free model
        if use_fallback:
            fallback_model = get_fallback_model(model)
            if fallback_model:
                print(f"Attempting fallback to {fallback_model}")
                return await query_model(
                    fallback_model,
                    messages,
                    timeout,
                    extract_final_content_flag,
                    use_fallback=False  # Don't recurse on fallback
                )
        
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    extract_final_content_flag: bool = False,
    use_fallback: bool = True
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model
        extract_final_content_flag: If True, extract only final content (remove reasoning tokens)
        use_fallback: If True, try fallback model if free model fails

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [
        query_model(
            model,
            messages,
            timeout=120.0,
            extract_final_content_flag=extract_final_content_flag,
            use_fallback=use_fallback
        )
        for model in models
    ]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}
