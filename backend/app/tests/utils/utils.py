"""General test utilities."""
import random
import string
import os

def random_lower_string(length: int = 32) -> str:
    """Generate a random lowercase string."""
    return "".join(random.choices(string.ascii_lowercase, k=length))

def random_email() -> str:
    """Generate a random email address."""
    return f"{random_lower_string()}@example.com"

def get_test_db_url() -> str:
    """Get the test database URL based on environment settings."""
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db-test")  # Using service name
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "test_db")

    # Use SQLite for local testing, PostgreSQL for Docker tests
    return (
        "sqlite+aiosqlite:///:memory:"
        if os.getenv("TEST_DB") == "sqlite"
        else f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    ) 