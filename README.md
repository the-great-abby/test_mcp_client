# MCP Chat Client

A real-time chat application with WebSocket support, built with FastAPI, PostgreSQL, and Redis.

## Features

- Real-time chat using WebSocket connections
- User authentication with JWT tokens
- Message history and persistence
- Rate limiting and connection management
- Health monitoring and telemetry
- Comprehensive test suite

## Project Structure

```
mcp_chat_client/
├── backend/                 # FastAPI backend
│   ├── app/                # Application code
│   │   ├── api/           # API endpoints and routers
│   │   ├── core/          # Core functionality
│   │   ├── db/            # Database models and sessions
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic services
│   ├── tests/             # Test suite
│   ├── alembic/           # Database migrations
│   └── Dockerfile         # Backend container definition
├── docker/                 # Docker configuration
│   ├── dev/               # Development environment
│   └── test/              # Test environment
├── docker-compose.dev.yml  # Development compose file
├── docker-compose.test.yml # Test compose file
└── .env.example           # Environment variables template
```

## Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Node.js 16+ (for frontend development)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mcp_chat_client.git
   cd mcp_chat_client
   ```

2. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

3. Update the `.env` file with your configuration:
   - Set your database credentials
   - Configure Redis settings
   - Set up JWT secret key
   - Configure API keys for AI services

4. Start the development environment:
   ```bash
   docker compose -f docker-compose.dev.yml up -d
   ```

5. Access the application:
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Development

### Backend Development

1. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

2. Run database migrations:
   ```bash
   ./run_migration.sh
   ```

3. Start the development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Testing

1. Start the test environment:
   ```bash
   docker compose -f docker-compose.test.yml up -d
   ```

2. Run the test suite:
   ```bash
   cd backend
   pytest
   ```

3. Generate coverage report:
   ```bash
   pytest --cov=app tests/
   ```

## API Documentation

The API documentation is available at `/docs` when running the application. It includes:

- REST API endpoints
- WebSocket connection details
- Authentication requirements
- Request/response schemas

## Environment Variables

See `.env.example` for all required environment variables. Key variables include:

- Database configuration (PostgreSQL)
- Redis settings
- JWT configuration
- WebSocket settings
- Test environment settings
- Monitoring configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 