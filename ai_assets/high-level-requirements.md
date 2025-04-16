# Requirements

## Infrastructure Requirements
* Must use docker
  * Docker version >= 24.0
  * Docker Compose version >= 2.0
  * All services must be containerized
  * Container health checks must be implemented
  * Must use docker as the development/testing environment
  * Must use docker for running tests

## Technology Stack
* Must have a typescript frontend
  * TypeScript version >= 5.0
  * Node.js version >= 20.0 LTS
  * React version >= 18.0
  * Must use strict TypeScript configuration
  
* Must have a python backend
  * Python version >= 3.11
  * FastAPI framework >= 0.100
  * SQLAlchemy >= 2.0
  * Alembic for migrations
  * Pydantic >= 2.0 for data validation
  * Testing requirements/dependencies must be in requirements-test.txt

## Build and Development
* Docker containers must build
  * Build time < 5 minutes
  * Multi-stage builds for production
  * Development builds with hot-reload
  * Optimized layer caching

* Must use makefiles because I can't remember commands
  * `Makefile` for human-readable commands
  * `Makefile.ai` for AI-specific commands
  * Clear documentation for each command
  * Consistent naming conventions

## Testing Requirements
* Unit tests must be used
  * Minimum 80% code coverage
  * Frontend: Jest + React Testing Library
  * Backend: Pytest
  * Integration tests for API endpoints
  * E2E tests for critical paths
  * Test reports in JUnit format

* Tests should be tested/confirmed to be working correctly after major changes/sections of code updated
  * Automated test runs on changes
  * Test results must be logged
  * Failed tests must block deployments
  * Performance regression tests

## Development Workflow
* Please list out the steps that you are taking as you're taking them
  * Clear commit messages
  * Step-by-step documentation
  * Change logs maintained
  * Impact assessment for changes

* Use test driven development where possible
  * Write tests first
  * Red-Green-Refactor cycle
  * Document test scenarios
  * Mock external dependencies

## Project Structure
* Task-master commands are executed from the project root directory
  * Tasks tracked in tasks.json
  * Priority levels defined
  * Dependencies documented
  * Deferred items clearly marked

* The project root directory ($HOME/code/ai_projects/mcp_chat_client)
  * Consistent directory structure
  * Clear separation of concerns
  * Documentation in relevant directories
  * Asset organization guidelines

## Command Execution
* The user executes all commands from the project root directory
  * Clear error messages
  * Command validation
  * Environment checks
  * Helpful usage examples

## AI Integration
* An AI Friendly set of commands (made available via the `Makefile.ai`)
  * Non-blocking commands for AI use
  * Consistent output formats
  * Error handling suitable for AI parsing
  * Clear separation from human commands

## Security Requirements
* Authentication and Authorization
  * JWT-based authentication
  * Role-based access control
  * Secure password handling
  * Session management

* Data Protection
  * HTTPS/WSS for all connections
  * Input validation
  * SQL injection prevention
  * XSS protection

## Performance Requirements
* Response Times
  * API responses < 200ms
  * WebSocket latency < 100ms
  * Page load time < 2s
  * Time to interactive < 3s

* Resource Usage
  * Memory usage < 512MB per container
  * CPU usage < 80% under normal load
  * Connection pooling for databases
  * Caching strategy defined

## Documentation
* API Documentation
  * OpenAPI/Swagger specs
  * Example requests/responses
  * Error codes documented
  * Rate limits specified

* Setup Instructions
  * Development environment setup
  * Production deployment guide
  * Configuration options
  * Troubleshooting guide

## Error Handling
* Logging
  * Structured log format
  * Log levels properly used
  * Request/Response logging
  * Error tracking

* Error Recovery
  * Graceful degradation
  * Circuit breakers
  * Retry strategies
  * Backup procedures

## AI Assistant Guidelines
* Command Response Format
  * Each command must return structured output
  * Exit codes must be clearly indicated
  * Error messages must be machine-parseable
  * Progress indicators must be standardized

* State Management
  * Each command must be idempotent where possible
  * State changes must be explicitly logged
  * Rollback procedures must be available
  * Current state must be queryable

* Tool Usage Patterns
  * Prefer non-blocking commands
  * Include timeout mechanisms
  * Provide progress feedback
  * Support graceful interruption

## AI-Specific Error Recovery
* Command Failures
  * Automatic retry with exponential backoff
  * Clear error categorization
  * Alternative command suggestions
  * State recovery procedures

* Validation Checks
  * Pre-command environment validation
  * Post-command state verification
  * Resource availability checks
  * Configuration consistency checks

## AI Workflow Integration
* Task Tracking
  * Automatic task status updates
  * Dependency tracking
  * Progress metrics
  * Completion verification

* Context Management
  * Session state persistence
  * Environment variable tracking
  * Configuration change logging
  * Resource usage monitoring

## AI-Human Handoff
* Status Reporting
  * Clear progress indicators
  * Decision points documented
  * Blocking issues highlighted
  * Next steps outlined

* Debugging Support
  * Detailed error context
  * Relevant log excerpts
  * Configuration dumps
  * State transition history