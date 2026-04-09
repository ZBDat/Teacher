"""Application configuration loaded from environment variables."""

import os


class Settings:
    """Central config object.  All values can be overridden via environment variables."""

    # OpenAI
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o")

    # File upload
    UPLOAD_DIR: str = os.environ.get("UPLOAD_DIR", "/tmp/teacher_uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50"))

    # Server
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8000"))
    CORS_ORIGINS: list[str] = os.environ.get("CORS_ORIGINS", "*").split(",")


settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
