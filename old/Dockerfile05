# --- Dockerfile ---

# Use a lean official Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for PyTorch and git (for cloning TinyTorch)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies first
COPY requirements.txt .

# Install PyTorch and other requirements
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Clone and install TinyTorch from GitHub
# Since it's not on PyPI yet, we install from source
RUN git clone https://github.com/MLSysBook/TinyTorch.git /tmp/tinytorch && \
    cd /tmp/tinytorch && \
    pip install -e . && \
    cd /app

# Copy the application code
COPY . .

# Environment variable for the port (Render injects this)
ENV PORT=10000
EXPOSE ${PORT}

# Command to run the service using Gunicorn
# Note: Gunicorn doesn't expand ${PORT} in CMD, so we use shell form
CMD gunicorn --bind 0.0.0.0:$PORT app:app
