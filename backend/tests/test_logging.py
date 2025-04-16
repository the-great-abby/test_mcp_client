import os
import logging
import pytest
from app.core.logging import setup_logging, LogLevel
import json
import sys
from io import StringIO

@pytest.fixture
def capture_logs():
    """Capture logs in a StringIO buffer"""
    string_buffer = StringIO()
    yield string_buffer

@pytest.fixture(autouse=True)
def clean_logging():
    """Reset logging configuration before each test"""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    yield
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

@pytest.mark.parametrize("log_level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_valid_log_levels(log_level: LogLevel, clean_logging):
    """Test that valid log levels are properly set"""
    os.environ["LOG_LEVEL"] = log_level
    setup_logging()
    root_logger = logging.getLogger()
    app_logger = logging.getLogger("app")
    
    assert root_logger.level == getattr(logging, log_level)
    assert app_logger.level == getattr(logging, log_level)

def test_invalid_log_level_defaults_to_info(clean_logging):
    """Test that invalid log levels default to INFO"""
    os.environ["LOG_LEVEL"] = "INVALID"
    setup_logging()
    root_logger = logging.getLogger()
    app_logger = logging.getLogger("app")
    
    assert root_logger.level == logging.INFO
    assert app_logger.level == logging.INFO

def test_lowercase_log_level(clean_logging):
    """Test that lowercase log levels are converted to uppercase"""
    os.environ["LOG_LEVEL"] = "debug"
    setup_logging()
    root_logger = logging.getLogger()
    app_logger = logging.getLogger("app")
    
    assert root_logger.level == logging.DEBUG
    assert app_logger.level == logging.DEBUG

def test_json_log_format(capture_logs, clean_logging):
    """Test that logs are properly formatted as JSON"""
    setup_logging(output_stream=capture_logs)
    logger = logging.getLogger("app")
    
    test_message = "Test log message"
    logger.info(test_message)
    
    # Get the log output
    log_output = capture_logs.getvalue().strip()
    log_entry = json.loads(log_output)
    
    assert log_entry["level"] == "INFO"
    assert log_entry["message"] == test_message
    assert "timestamp" in log_entry
    assert log_entry["module"] == "test_logging"
    assert log_entry["function"] == "test_json_log_format"

def test_request_id_logging(clean_logging):
    """Test that request_id is included when present"""
    setup_logging()
    logger = logging.getLogger("app")
    
    # Create a log record with request_id
    record = logging.LogRecord(
        name="app",
        level=logging.INFO,
        pathname="test_logging.py",
        lineno=1,
        msg="Test with request ID",
        args=(),
        exc_info=None
    )
    record.request_id = "test-123"
    
    # Get the formatter
    formatter = logger.handlers[0].formatter
    log_entry = json.loads(formatter.format(record))
    
    assert log_entry["request_id"] == "test-123"

def test_exception_logging(capture_logs, clean_logging):
    """Test that exceptions are properly logged"""
    setup_logging(output_stream=capture_logs)
    logger = logging.getLogger("app")
    
    try:
        raise ValueError("Test error")
    except ValueError:
        logger.exception("An error occurred")
    
    # Get the log output
    log_output = capture_logs.getvalue().strip()
    log_entry = json.loads(log_output)
    
    assert log_entry["level"] == "ERROR"
    assert "exception" in log_entry
    assert "ValueError: Test error" in log_entry["exception"]

def test_third_party_logger_levels(clean_logging):
    """Test that third-party loggers are set to WARNING level"""
    setup_logging()
    
    assert logging.getLogger("uvicorn").level == logging.WARNING
    assert logging.getLogger("fastapi").level == logging.WARNING
    assert logging.getLogger("sqlalchemy").level == logging.WARNING 