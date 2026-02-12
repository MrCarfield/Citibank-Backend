from app.services.llm_council.core import run_full_council

async def get_council_response(prompt: str) -> str:
    """
    Simple wrapper to get the final response from the LLM Council.
    
    Args:
        prompt: The user's input prompt/question
        
    Returns:
        str: The final synthesized response from the Chairman
    """
    result = await run_full_council(prompt)
    return result.get("final_response", "Error processing request")

async def get_council_response_full(prompt: str) -> dict:
    """
    Get the full details of the council process including individual responses and rankings.
    
    Args:
        prompt: The user's input prompt/question
        
    Returns:
        dict: Dictionary containing 'final_response' and 'details'
    """
    return await run_full_council(prompt)
