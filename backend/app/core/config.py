from typing import Any, Optional, Literal, List, Union
import os
from pydantic_settings import BaseSettings
from pydantic import validator, AnyHttpUrl

class Settings(BaseSettings):
    PROJECT_NAME: str = "MCP Chat"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    NODE_ENV: str = "development"
    
    @validator("LOG_LEVEL", pre=True)
    def uppercase_log_level(cls, v: str) -> str:
        return v.upper() if isinstance(v, str) else v
    
    # PostgreSQL
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "test_mcp_chat")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # For test environment, use SQLite if TEST_DB is set to "sqlite"
        if os.getenv("TEST_DB") == "sqlite":
            return "sqlite+aiosqlite:///:memory:"
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis-test")  # Default to docker-compose service name
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
    REDIS_TIMEOUT: int = int(os.getenv("REDIS_TIMEOUT", "5"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    @property
    def REDIS_URI(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")  # Change in production!
    ALGORITHM: str = "HS256"
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
    WS_RATE_LIMIT: int = 60
    WS_MAX_MESSAGE_LENGTH: int = 4096  # Maximum length of a chat message
    
    # API settings
    API_V1_STR: str = "/api/v1"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000"  # React frontend
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 