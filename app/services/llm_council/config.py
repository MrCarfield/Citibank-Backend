from typing import List
from pydantic_settings import BaseSettings

class LLMCouncilConfig(BaseSettings):
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    
    # Default models if not provided in env
    COUNCIL_MODELS: List[str] = [
        "openai/gpt-4o",
        "google/gemini-1.5-pro",
        "anthropic/claude-3.5-sonnet",
        "x-ai/grok-2-1212",
    ]
    
    CHAIRMAN_MODEL: str = "google/gemini-1.5-pro"

    class Config:
        env_file = ".env"
        extra = "ignore" # Ignore other env vars

llm_config = LLMCouncilConfig()
