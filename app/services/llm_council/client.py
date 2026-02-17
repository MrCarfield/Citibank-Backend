import httpx
from typing import List, Dict, Any, Optional
from app.services.llm_council.config import llm_config

async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.
    """
    if not llm_config.OPENROUTER_API_KEY:
        print("Warning: OPENROUTER_API_KEY is not set")
        return None

    headers = {
        "Authorization": f"Bearer {llm_config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/citibank-backend", # Required by OpenRouter for some tiers
        "X-Title": "Citibank Backend LLM Council",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                llm_config.OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
        
            if 'error' in data:
                print(f"API Error from {model}: {data['error']}")
                return None
                
            if not data.get('choices'):
                print(f"No choices returned from {model}")
                return None

            message = data['choices'][0]['message']

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')
            }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.
    """
    import asyncio

    tasks = [query_model(model, messages) for model in models]


    responses = await asyncio.gather(*tasks)


    return {model: response for model, response in zip(models, responses)}
