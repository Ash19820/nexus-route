from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    FAST_TIER_URL: str = "https://api.groq.com/openai/v1/chat/completions"
    FAST_TIER_KEY: str = ""
    FAST_TIER_MODEL: str = "llama-3.1-8b-instant"

    REASONING_TIER_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    REASONING_TIER_KEY: str = ""
    REASONING_TIER_MODEL: str = "gemini-2.5-flash"

    ROUTING_SIMILARITY_THRESHOLD: float = 0.62

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
