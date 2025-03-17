FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Los_Angeles

# Install essential system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tzdata \
        dos2unix \
        ca-certificates \
        bash \
        wget \
        gnupg \
        libcap2-bin \
        libglib2.0-0 \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libxcb1 \
        libxkbcommon0 \
        libx11-6 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        libasound2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Playwright dependencies and create browser directory
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir -p /ms-playwright && \
    chown -R root:root /ms-playwright && \
    chmod -R 755 /ms-playwright && \
    # Create a .placeholder file to ensure mount point permissions are correct
    touch /ms-playwright/.placeholder && \
    chmod 644 /ms-playwright/.placeholder

# Install Playwright from requirements.txt
COPY requirements.txt .
RUN PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 pip install --no-cache-dir -r requirements.txt && \
    # Show installed version for verification
    echo "Playwright $(pip show playwright | grep Version) installed" && \
    # Install system dependencies for Playwright
    apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libatspi2.0-0 \
        libwayland-client0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create application directory and subdirectories
WORKDIR /app
RUN mkdir -p /app/data /app/configs /app/logs

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure entrypoint script has correct line endings and is executable
RUN ls -la && \
    cat docker/entrypoint.sh | head -1 && \
    dos2unix docker/entrypoint.sh && \
    chmod +x docker/entrypoint.sh && \
    ls -la docker/entrypoint.sh
# Set up Chrome sandbox and capabilities
RUN mkdir -p /tmp/.chrome-sandbox && \
    chown root:root /tmp/.chrome-sandbox && \
    chmod 4755 /tmp/.chrome-sandbox && \
    # Add special capabilities for running Chrome without sandbox
    setcap cap_net_raw,cap_net_admin,cap_net_bind_service=+ep /ms-playwright/.placeholder

# Set entrypoint
ENTRYPOINT ["/bin/bash", "/app/docker/entrypoint.sh"]