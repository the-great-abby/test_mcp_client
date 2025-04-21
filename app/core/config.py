from typing import List, Optional
from pydantic import BaseSettings, AnyHttpUrl, PostgresDsn, field_validator, ConfigDict
import os

class Settings(BaseSettings):
    model_config = ConfigDict(case_sensitive=True, env_file=".env")

    PROJECT_NAME: str = "MCP Chat"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    NODE_ENV: str = "development"

    # Database settings
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db-test")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "mcp_chat")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Get the database URI, either from DATABASE_URL or individual components."""
        if database_url := os.getenv("DATABASE_URL"):
            return database_url

        return PostgresDsn.build(
            scheme="postgresql",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=f"/{self.POSTGRES_DB}",
        )

    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis-test")
    REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
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

    @field_validator("LOG_LEVEL", pre=True)
    def validate_log_level(cls, v: str) -> str:
        """Validate and normalize log level."""
        return v.upper() if isinstance(v, str) else v 