FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create and set working directory
WORKDIR /app

# Install uv
## The installer requires curl (and certificates) to download the release archive
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

## Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

## Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

## Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Copy project files
COPY . .

# Install dependencies
RUN uv sync --locked --no-cache-dir

# Path
ENV PATH="/app/.venv/bin:$PATH"

# Install browsers
RUN playwright install --with-deps chromium

CMD ["lunchbuddy"]
