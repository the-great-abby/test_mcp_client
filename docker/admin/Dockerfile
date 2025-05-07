FROM python:3.11-slim

WORKDIR /admin

# Install system dependencies
RUN apt-get update && apt-get install -y git universal-ctags && rm -rf /var/lib/apt/lists/*

# Copy requirements for admin scripts (if any)
COPY admin/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy admin scripts and rules
COPY maintain_rules.py ./
COPY .cursor/rules/ ./.cursor/rules/
COPY Makefile.ai ./
COPY admin/scripts/ ./scripts/

# Set default command
CMD ["bash"] 
