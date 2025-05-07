FROM python:3.11-slim
WORKDIR /app
COPY main.py ./
COPY ../onboarding.yaml ../.ai-ide-config.json ../docs/ ../.cursor/rules/ ./
RUN pip install fastapi uvicorn pyyaml
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"] 