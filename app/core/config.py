from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # OpenRouter
    openrouter_api_key: str
    openrouter_api_base: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-chat"
    
    # Clerk
    firebase_secret_key: str
    firebase_project_id: str
    firebase_auth_domain: str
    
    # Optional: Add other common settings
    debug: bool = False
    environment: str = "development"
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Create settings instance
settings = Settings()


def get_settings() -> Settings:
    return Settings()