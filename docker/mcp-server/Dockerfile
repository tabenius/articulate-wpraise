FROM python:3.12-slim

WORKDIR /app

# Install system dependencies and Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# Copy source code first (needed for package installation)
COPY mcp-server/ ./
# Copy helper scripts (e.g., setup-remote-wordpress.py) so WP-CLI fallback works in container
COPY scripts/ ./scripts/
# Also copy scripts to the container root so the module-level relative lookup succeeds
COPY scripts/ /scripts/

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "articulate_mcp.server"]
