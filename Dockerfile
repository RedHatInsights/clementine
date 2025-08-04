# Simple, Secure Dockerfile for Clementine Slack Bot
FROM registry.redhat.io/ubi9/python-311@sha256:ff8dda0a09e63d9b3b108669200ec3399a4abd6c8276b1cf769eee093563ec74

# Metadata
LABEL name="clementine-slack-bot" \
      description="Clementine Slack Bot - AI-powered assistant for Slack"

# Install Python dependencies
COPY Pipfile Pipfile.lock ./
RUN pip install --no-cache-dir pipenv && \
    pipenv install --system --deploy && \
    pip uninstall -y pipenv

# Create non-root user
RUN groupadd -r -g 1001 clementine && \
    useradd -r -g clementine -u 1001 -d /app clementine

# Copy application code
WORKDIR /app
COPY --chown=clementine:clementine clementine/ ./clementine/
COPY --chown=clementine:clementine app.py ./

# Create data directory
RUN mkdir -p /app/data && chown clementine:clementine /app/data

# Switch to non-root user
USER 1001

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO \
    BOT_NAME=Clementine

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD pgrep -f "python.*app.py" || exit 1

# Run the application
CMD ["python", "app.py"] 