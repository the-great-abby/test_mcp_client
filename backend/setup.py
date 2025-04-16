from setuptools import setup, find_packages

setup(
    name="mcp-chat-backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn>=0.23.1",
        "sqlalchemy>=2.0.27",
        "alembic>=1.13.1",
        "psycopg2-binary>=2.9.9",
        "redis>=5.0.1",
        "pydantic>=2.7.2,<3.0.0",
        "pydantic-settings>=2.1.0",
        "python-dotenv>=1.0.1",
        "python-jose>=3.3.0",
        "passlib>=1.7.4",
        "bcrypt>=4.1.2",
        "python-multipart>=0.0.9",
        "aiofiles>=23.2.1",
        "httpx>=0.26.0",
        "mcp-server>=0.1.0",
    ],
) 