from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_url: str = "postgresql+asyncpg://docstore:changeme@postgres:5432/docstore"
    rag_service_url: str = "http://rag_service:8001"
    api_gateway_url: str = "http://api_gateway:8000"
    gw_service_email: str = "admin1@example.com"
    gw_service_pass: str = "changeme"

    # AWS / Bedrock
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    bedrock_llm_model: str = "us.anthropic.claude-opus-4-5-20251101-v1:0"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
