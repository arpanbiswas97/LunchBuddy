FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create and set working directory
WORKDIR /app

# Install uv (used for dependency management)
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN uv sync --locked

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["uv", "run", "lunchbuddy"]
