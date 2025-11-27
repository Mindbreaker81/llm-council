"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple, Optional
from .openrouter import query_models_parallel, query_model
from .config import (
    COUNCIL_MODELS_PREMIUM,
    CHAIRMAN_MODEL_PREMIUM,
    COUNCIL_MODELS_ECONOMIC,
    CHAIRMAN_MODEL_ECONOMIC,
    COUNCIL_MODELS_FREE,
    CHAIRMAN_MODEL_FREE,
    COUNCIL_TYPE_PREMIUM,
    COUNCIL_TYPE_ECONOMIC,
    COUNCIL_TYPE_FREE,
    COUNCIL_MODELS,
    CHAIRMAN_MODEL,
)


def get_council_config(council_type: str = COUNCIL_TYPE_PREMIUM) -> Tuple[List[str], str]:
    """
    Get council models and chairman model based on council type.

    Args:
        council_type: Type of council ("premium", "economic", or "free")

    Returns:
        Tuple of (council_models list, chairman_model string)
    """
    if council_type == COUNCIL_TYPE_ECONOMIC:
        return COUNCIL_MODELS_ECONOMIC, CHAIRMAN_MODEL_ECONOMIC
    elif council_type == COUNCIL_TYPE_FREE:
        return COUNCIL_MODELS_FREE, CHAIRMAN_MODEL_FREE
    else:
        return COUNCIL_MODELS_PREMIUM, CHAIRMAN_MODEL_PREMIUM


async def stage1_collect_responses(
    user_query: str,
    council_models: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        council_models: List of model identifiers to use. If None, uses default.

    Returns:
        List of dicts with 'model', 'response' (final content), and 'original_response' (with reasoning) keys
    """
    if council_models is None:
        council_models = COUNCIL_MODELS

    messages = [{"role": "user", "content": user_query}]

    # Query all models in parallel (don't extract final content yet - keep reasoning for transparency)
    responses = await query_models_parallel(
        council_models,
        messages,
        extract_final_content_flag=False,
        use_fallback=True
    )

    # Format results - keep original for user transparency, extract final for Stage 2
    stage1_results = []
    print(f"DEBUG: Processing {len(responses)} responses from models")
    for model, response in responses.items():
        if response is None:
            print(f"DEBUG: {model} returned None (failed)")
            continue
            
        original_content = response.get('original_content', '')
        final_content = response.get('content', '')
        
        print(f"DEBUG: {model} - original_content: {len(original_content) if original_content else 0} chars, final_content: {len(final_content) if final_content else 0} chars")
        
        # If both are empty, skip this response
        if not original_content and not final_content:
            print(f"DEBUG: Skipping {model} - both original_content and content are empty")
            continue
        
        # Use final_content if available, otherwise use original_content
        display_content = final_content if final_content else original_content
        original_display = original_content if original_content else final_content
        
        stage1_results.append({
            "model": model,
            "response": display_content,  # Content to display (final or original)
            "original_response": original_display  # Original with reasoning tokens for transparency
        })
        print(f"DEBUG: Added {model} to stage1_results (response length: {len(display_content)})")
    
    print(f"DEBUG: stage1_collect_responses returning {len(stage1_results)} results")
    if stage1_results:
        print(f"DEBUG: First result model: {stage1_results[0]['model']}, response length: {len(stage1_results[0]['response'])}")
    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    council_models: Optional[List[str]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        council_models: List of model identifiers to use. If None, uses default.

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    if council_models is None:
        council_models = COUNCIL_MODELS

    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    # Extract final content to save tokens (remove reasoning tokens for Stage 2)
    responses = await query_models_parallel(
        council_models,
        messages,
        extract_final_content_flag=True,
        use_fallback=True
    )

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    chairman_model: Optional[str] = None,
    council_type: str = COUNCIL_TYPE_PREMIUM
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2
        chairman_model: Model identifier for chairman. If None, uses default.
        council_type: Type of council (for context limit detection)

    Returns:
        Dict with 'model' and 'response' keys
    """
    if chairman_model is None:
        chairman_model = CHAIRMAN_MODEL

    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    # Check context limits (free models typically have 32k limit)
    max_tokens = 32000 if council_type == COUNCIL_TYPE_FREE else 128000
    use_summary = check_context_limits(stage1_text, stage2_text, max_tokens)
    
    if use_summary:
        # Use summarized Stage 2 results to save tokens
        label_to_model = {
            f"Response {chr(65 + i)}": result['model']
            for i, result in enumerate(stage1_results)
        }
        stage2_summary = await summarize_stage2_results(stage2_results, label_to_model)
        stage2_text = f"Summary of Peer Rankings:\n{stage2_summary}"

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(chairman_model, messages, extract_final_content_flag=True)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": chairman_model,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": chairman_model,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def estimate_token_count(text: str) -> int:
    """
    Estimate token count for a text string.
    Rough approximation: 1 token ≈ 4 characters for English text.
    
    Args:
        text: Text to estimate
        
    Returns:
        Estimated token count
    """
    return len(text) // 4


def check_context_limits(
    stage1_text: str,
    stage2_text: str,
    max_tokens: int = 32000
) -> bool:
    """
    Check if context exceeds token limits.
    
    Args:
        stage1_text: Combined text from Stage 1
        stage2_text: Combined text from Stage 2
        max_tokens: Maximum token limit (default 32k for free models)
        
    Returns:
        True if context exceeds limits, False otherwise
    """
    total_tokens = estimate_token_count(stage1_text) + estimate_token_count(stage2_text)
    return total_tokens > max_tokens


async def summarize_stage2_results(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> str:
    """
    Summarize Stage 2 rankings into a concise "Bulletin of Ratings" using an economic model.
    
    This creates a hierarchical council that saves tokens while maintaining coherence.
    Uses Mistral Small as recommended in the technical documentation.
    
    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names
        
    Returns:
        Concise summary of rankings
    """
    # Build full rankings text
    rankings_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])
    
    summary_prompt = f"""Summarize the following peer rankings from an LLM Council into a concise "Bulletin of Ratings".
Focus on the key insights, patterns of agreement/disagreement, and overall assessment.
Keep it brief but informative.

Rankings:
{rankings_text}

Concise Summary:"""
    
    messages = [{"role": "user", "content": summary_prompt}]
    
    # Use Mistral Small for summarization (economic model as recommended)
    summary_model = "mistralai/mistral-small-24b-instruct-2501"
    response = await query_model(summary_model, messages, timeout=60.0, extract_final_content_flag=True)
    
    if response is None:
        # Fallback: return a simple summary
        return f"Peer rankings from {len(stage2_results)} models. See full rankings for details."
    
    return response.get('content', '')


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(
    user_query: str,
    council_type: str = COUNCIL_TYPE_PREMIUM
) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question
        council_type: Type of council to use ("premium" or "economic")

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Get council configuration based on type
    council_models, chairman_model = get_council_config(council_type)

    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query, council_models)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(
        user_query, stage1_results, council_models
    )

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        chairman_model,
        council_type
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "council_type": council_type
    }

    return stage1_results, stage2_results, stage3_result, metadata
