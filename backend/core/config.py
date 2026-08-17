from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SECRET_KEY: str = "your-jwt-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/agentflow"
    REDIS_URL: str = "redis://localhost:6379"

    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "ap-south-1"
    SQS_QUEUE_URL: str | None = None
    SQS_DLQ_URL: str | None = None

    OPENAI_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None


settings = Settings()
