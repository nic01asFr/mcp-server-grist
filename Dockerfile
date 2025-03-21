FROM python:3.11-slim AS builder

# Set up working directory
WORKDIR /app

# Copy requirements handling first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create a non-root user to run the server
RUN groupadd -r mcp && \
    useradd -r -g mcp mcp && \
    chown -R mcp:mcp /app

# Switch to non-root user
USER mcp

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the server
CMD ["python", "grist_mcp_server.py"]