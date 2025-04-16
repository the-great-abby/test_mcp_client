import logging
import sys
from typing import Any, Dict, Literal, Optional, TextIO
import json
from datetime import datetime, UTC
import os

# Valid log levels that match MCP's requirements
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
            
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def setup_logging(output_stream: Optional[TextIO] = None) -> None:
    """Configure logging with JSON formatting and appropriate log levels
    
    Args:
        output_stream: Optional stream to write logs to. Defaults to sys.stdout.
    """
    # Get log level from env and ensure it's uppercase and valid
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        log_level = "INFO"  # Default to INFO if invalid level provided
        
    # Remove any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    root_logger.setLevel(getattr(logging, log_level))
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(output_stream or sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # Set levels for third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    # Create a logger for our app
    app_logger = logging.getLogger("app")
    # Remove any existing handlers
    for handler in app_logger.handlers[:]:
        app_logger.removeHandler(handler)
    # Add the console handler to the app logger
    app_logger.addHandler(console_handler)
    app_logger.setLevel(getattr(logging, log_level))
    # Prevent propagation to avoid duplicate logs
    app_logger.propagate = False 