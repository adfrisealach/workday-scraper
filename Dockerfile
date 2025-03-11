FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Los_Angeles

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    dos2unix \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/data /app/configs /app/logs

# Set the timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create application directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories for mounted volumes
RUN mkdir -p /app/data /app/configs /app/logs

# Ensure entrypoint script has correct line endings and is executable
RUN dos2unix entrypoint.sh && \
    chmod +x entrypoint.sh && \
    sed -i -e 's/\r$//' entrypoint.sh

# Set up cron environment
ENV SHELL=/bin/sh
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Copy entrypoint to bin directory and make it executable
RUN cp entrypoint.sh /usr/local/bin/ && \
    chmod +x /usr/local/bin/entrypoint.sh && \
    ln -sf /usr/local/bin/entrypoint.sh /entrypoint.sh

# Set entrypoint using absolute path
ENTRYPOINT ["/entrypoint.sh"]