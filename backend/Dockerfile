### Development stage ###
FROM python:3.11-slim as development

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    iputils-ping \
    netcat-traditional \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-test.txt
RUN pip install pytest pytest-asyncio pytest-cov

# Set PYTHONPATH for module imports
ENV PYTHONPATH=/app

# Copy application code
COPY . /app/
RUN chmod +x /app/docker-entrypoint.sh

# Install the package in development mode
RUN pip install -e .

# Expose the port
EXPOSE 8000

# Set the entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Command to run the server in development mode with reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

### Production stage ###
FROM python:3.11-slim as production

WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (production only)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app .
COPY docker-entrypoint.sh .

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Expose the port
EXPOSE 8000

# Set the entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Command to run the server in production mode
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 