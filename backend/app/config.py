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
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_TRACING: bool = True
    LANGSMITH_PROJECT: str = "medclaim-dev"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"

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

    PROJECT_NAME: str = "MedClaim"
    VERSION: str = "1.0.0"

    # CORS Origins - can be overridden by FRONTEND_URL env var
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Get CORS origins from environment or defaults."""
        origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            self.FRONTEND_URL,
        ]
        # Add production frontend URL if set
        if self.APP_ENV == "production" and self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins

    CORS_HEADERS: list[str] = ["Content-Type", "Authorization", "Accept"]
    CORS_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    ENABLE_METRICS: bool = True

    # Swagger UI Authentication
    SWAGGER_USERNAME: str = "admin"
    SWAGGER_PASSWORD: str = "medclaim123"


# Singleton settings instance
settings = Settings()
