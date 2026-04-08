FROM python:3.11-slim

# Copy the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install build dependencies for packages like curl-cffi
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the project files first to leverage Docker's layer caching
COPY pyproject.toml .
# Sync dependencies (this creates the .venv automatically)
RUN uv sync --no-install-project

# Now copy the rest of the application
COPY . .

# Final installation of the current project into the venv
RUN uv sync

EXPOSE 8010
# Use uv run to execute uvicorn within the managed virtual environment
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
