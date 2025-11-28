# Multi-stage Dockerfile for Jobly scraper and processor
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY jobly ./jobly
COPY scripts ./scripts

# Install Python dependencies and the package
RUN pip install -e .

# Install Playwright and Chromium browser
RUN playwright install chromium && \
    playwright install-deps chromium

# Create non-root user for security
RUN useradd -m -u 1000 jobly && \
    chown -R jobly:jobly /app

USER jobly

# Default command (override in docker-compose)
CMD ["python", "scripts/run_scraper.py"]
