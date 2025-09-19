# app/core/config.py
from pydantic import Field, AnyUrl
from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # --- Application Core Settings ---
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    BACKEND_CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"], env="BACKEND_CORS_ORIGINS")
    
    # --- Project Metadata ---
    PROJECT_NAME: str = Field(default="AI Astrology Chatbot", env="PROJECT_NAME")
    PROJECT_VERSION: str = Field(default="0.1.0", env="PROJECT_VERSION")
    API_V1_STR: str = Field(default="/api", env="API_V1_STR")
    
    # --- Database Settings (PostgreSQL) ---
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # --- Redis Settings ---
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # --- Firebase Settings ---
    FIREBASE_PROJECT_ID: str = Field(..., env="FIREBASE_PROJECT_ID")
    FIREBASE_PRIVATE_KEY: str = Field(..., env="FIREBASE_PRIVATE_KEY")
    FIREBASE_CLIENT_EMAIL: str = Field(..., env="FIREBASE_CLIENT_EMAIL")
    FIREBASE_AUTH_DOMAIN: str = Field(..., env="FIREBASE_AUTH_DOMAIN")
    FIREBASE_SERVICE_ACCOUNT_PATH: str = Field(..., env="FIREBASE_SERVICE_ACCOUNT_PATH")    
    # --- OpenRouter API Settings ---
    OPENROUTER_API_KEY: str = Field(..., env="OPENROUTER_API_KEY")
    OPENROUTER_API_BASE: str = Field(default="https://openrouter.ai/api/v1", env="OPENROUTER_API_BASE")
    OPENROUTER_MODEL: str = Field(default="deepseek/deepseek-chat", env="OPENROUTER_MODEL")
    OPENROUTER_HTTP_REFERER: str = Field(default="https://openrouter.ai", env="OPENROUTER_HTTP_REFERER")
    OPENROUTER_APP_TITLE: str = Field(default="OpenRouter", env="OPENROUTER_APP_TITLE")
    # Redis Settings
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    REDIS_MAX_CONNECTIONS: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")
    REDIS_SESSION_TTL: int = Field(default=86400, env="REDIS_SESSION_TTL")  # 24 hours
    REDIS_CACHE_TTL: int = Field(default=3600, env="REDIS_CACHE_TTL")  # 1 hour
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=3600, env="RATE_LIMIT_WINDOW") 
    
    # --- Encryption Settings ---
    ENCRYPTION_SECRET_KEY: str = Field(..., env="ENCRYPTION_SECRET_KEY")
    
    # Derived properties
    @property
    def IS_PRODUCTION(self):
        return self.ENVIRONMENT == "production"
    
    @property
    def IS_DEVELOPMENT(self):
        return self.ENVIRONMENT == "development"
    
    @property
    def async_database_url(self):
        """Ensure the DATABASE_URL uses the asyncpg driver."""
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.DATABASE_URL

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create a global settings instance
settings = Settings()