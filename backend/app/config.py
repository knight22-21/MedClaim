"""
MedClaim — Application Settings

Loads configuration from environment variables using pydantic-settings.
All external service credentials and application toggles are centralized here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from .env file and environment variables.
    Environment variables take precedence over .env values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- LLM Providers ---
    GROQ_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # --- Vector Database (Qdrant Cloud) ---
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""

    # --- Persistence (Supabase) ---
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # --- LLMOps (LangSmith) ---
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_PROJECT: str = "medclaim-dev"

    # --- Task Queue (Upstash Redis) ---
    UPSTASH_REDIS_URL: str = ""
    UPSTASH_REDIS_TOKEN: str = ""

    # --- Notifications (Resend) ---
    RESEND_API_KEY: str = ""

    # --- EHR Integration ---
    HAPI_FHIR_URL: str = "http://localhost:8080/fhir"

    # --- Voice AI (Optional) ---
    ELEVEN_LABS_API_KEY: str = ""

    # --- Application Config ---
    APP_ENV: str = "development"
    MARKET: str = "US"  # US or INDIA
    LOG_LEVEL: str = "DEBUG"


# Singleton settings instance
settings = Settings()
