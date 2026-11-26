# =============================================================================
# CareFlow AI — Multi-stage Production Dockerfile
# =============================================================================

# Stage 1: Build React/TypeScript Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend & Unified Server
FROM python:3.11-slim
WORKDIR /app

# Install system audio & build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend, voice-agent, and configuration
COPY backend/ ./backend/
COPY voice-agent/ ./voice-agent/
COPY voice_agent/ ./voice_agent/
COPY .env.example ./.env.example

# Copy compiled frontend distribution from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Seed database with initial doctors and slots
ENV PYTHONPATH="."
RUN python -c "from backend.app.db.seed import seed_database; seed_database(reset=True)"

# Default environment configuration
ENV PORT=8000
ENV HOST=0.0.0.0
ENV DATABASE_URL="sqlite:///./careflow.db"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
