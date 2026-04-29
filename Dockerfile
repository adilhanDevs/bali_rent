FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN addgroup --system django && \
    adduser --system --group django

# Set work directory and permissions
WORKDIR /app
RUN chown django:django /app

# Copy entrypoint script
COPY --chown=django:django entrypoint.sh .
RUN sed -i 's/\r$//g' /app/entrypoint.sh
# Copy project
COPY --chown=django:django . .

RUN chmod +x /app/entrypoint.sh && sed -i 's/\r$//g' /app/entrypoint.sh

RUN mkdir -p /app/static_files /app/media && chown django:django /app/static_files /app/media

# Use non-root user
USER django

# Run entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
