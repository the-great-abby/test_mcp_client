from typing import Any, Optional, Literal, List, Union
import os
from pydantic_settings import BaseSettings
from pydantic import validator, AnyHttpUrl, Field, ConfigDict
from pydantic.networks import PostgresDsn
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
import logging
import secrets
from zoneinfo import ZoneInfo

# Load environment variables from .env file if it exists
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

UTC = ZoneInfo("UTC")

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="allow")

    PROJECT_NAME: str = "MCP Chat"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    NODE_ENV: str = "development"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    @validator("LOG_LEVEL", pre=True)
    def uppercase_log_level(cls, v: str) -> str:
        return v.upper() if isinstance(v, str) else v
    
    # PostgreSQL
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "test_mcp_chat")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    SQL_ECHO: bool = False
    
    @validator("POSTGRES_PORT", pre=True)
    def validate_postgres_port(cls, v: Union[str, int]) -> int:
        """Validate and convert POSTGRES_PORT to integer."""
        if isinstance(v, str):
            return int(v)
        return v
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Get the database URI, either from DATABASE_URL or individual components."""
        print("DEBUG: Checking for DATABASE_URL environment variable...")
        if database_url := os.getenv("DATABASE_URL"):
            print(f"DEBUG: Found DATABASE_URL={database_url}")
            # Ensure +asyncpg is added if missing, for safety
            if "+asyncpg" not in database_url:
                if "postgresql://" in database_url:
                    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
                    print(f"DEBUG: Modified DATABASE_URL to add +asyncpg: {database_url}")
                elif "postgres://" in database_url:
                     database_url = database_url.replace("postgres://", "postgresql+asyncpg://")
                     print(f"DEBUG: Modified legacy DATABASE_URL to add +asyncpg: {database_url}")

            final_url = database_url.replace("postgres://", "postgresql://") # Keep original replacement for legacy postgres://
            print(f"DEBUG: Returning URI from DATABASE_URL env var: {final_url}")
            return final_url

        print("DEBUG: DATABASE_URL not set, building DSN...")
        # Build the DSN with proper parameter names for Pydantic v2
        dsn = PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=int(self.POSTGRES_PORT),
            path=self.POSTGRES_DB  # Removed leading slash
        )
        final_url = str(dsn)
        print(f"DEBUG: Returning URI built from DSN: {final_url}")
        return final_url
    
    @property
    def DATABASE_URL(self) -> str:
        """Alias for SQLALCHEMY_DATABASE_URI for backward compatibility."""
        return self.SQLALCHEMY_DATABASE_URI
    
    @property
    def TEST_DATABASE_URL(self) -> str:
        """Get the test database URL."""
        if database_url := os.getenv("TEST_DATABASE_URL"):
            return database_url.replace("postgres://", "postgresql://")

        # Build the DSN with proper parameter names for Pydantic v2
        dsn = PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=int(self.POSTGRES_PORT),
            path="test_db"  # Updated to match docker-compose.test.yml
        )
        return str(dsn)
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis-test")  # Default to docker-compose service name
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
    REDIS_TIMEOUT: int = int(os.getenv("REDIS_TIMEOUT", "5"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    REDIS_SSL: bool = os.getenv("REDIS_SSL", "false").lower() == "true"
    
    @property
    def REDIS_URI(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # Change in production!
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Model Settings
    MODEL_API_KEY: str = ""
    MODEL_NAME: str = "claude-3-sonnet-20240229"
    MODEL_TEMPERATURE: float = 0.7
    MODEL_MAX_TOKENS: int = 4000
    MODEL_PROVIDER: str = "anthropic"
    ANTHROPIC_API_KEY: Optional[str] = None
    MODEL: Optional[str] = None
    MAX_TOKENS: Optional[int] = None
    TEMPERATURE: Optional[float] = None
    
    # Perplexity settings
    PERPLEXITY_API_KEY: str = ""
    PERPLEXITY_MODEL: str = "sonar-pro"
    
    # Task settings
    DEFAULT_SUBTASKS: int = 3
    DEFAULT_PRIORITY: str = "medium"
    
    # MCP settings
    MCP_HOST: str = os.getenv("MCP_HOST", "backend")
    MCP_PORT: int = int(os.getenv("MCP_PORT", "8000"))
    
    @property
    def MCP_WEBSOCKET_URL(self) -> str:
        return f"ws://{self.MCP_HOST}:{self.MCP_PORT}/ws"
    
    @property
    def MCP_HTTP_URL(self) -> str:
        return f"http://{self.MCP_HOST}:{self.MCP_PORT}"
    
    # WebSocket settings
    WS_MAX_CONNECTIONS_PER_USER: int = 5
    WS_PING_INTERVAL: float = 20.0  # Seconds
    WS_PING_TIMEOUT: float = 20.0  # Seconds
    WS_CLOSE_TIMEOUT: float = 20.0  # Seconds
    WS_MAX_HISTORY_SIZE: int = 100
    WS_MAX_MESSAGES_PER_SECOND: int = 60  # Maximum messages per second per user
    WS_MAX_MESSAGE_LENGTH: int = 4096  # Maximum length of a chat message
    
    # API settings
    API_V1_STR: str = "/api/v1"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000"  # React frontend
    ]

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Create global settings instance
settings = get_settings() 