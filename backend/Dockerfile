FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml .
COPY CLAUDE.md .
COPY README.md .
COPY backend/ backend/

# Create data directory
RUN mkdir -p data/conversations

# Install dependencies
RUN uv sync

# Expose port
EXPOSE 8001

# Run the application
CMD ["uv", "run", "python", "-m", "backend.main"]
