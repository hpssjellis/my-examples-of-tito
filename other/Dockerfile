# --- Cloud-Native TinyTorch API Dockerfile ---
# This adapts the local-first TinyTorch setup for cloud deployment

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Clone TinyTorch repository
RUN git clone https://github.com/MLSysBook/TinyTorch.git /app/TinyTorch

# Change to TinyTorch directory - this is important!
WORKDIR /app/TinyTorch

# Instead of running setup-environment.sh (which creates a venv), 
# we'll manually do what it does but in our Docker environment

# Install Python dependencies that setup-environment.sh would install
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    numpy \
    torch --extra-index-url https://download.pytorch.org/whl/cpu \
    pytest \
    jupytext \
    pyyaml \
    rich \
    matplotlib \
    jupyter \
    jupyterlab \
    notebook \
    nbformat \
    nbconvert \
    ipykernel

# Install Flask and gunicorn for the API
RUN pip install --no-cache-dir \
    Flask \
    Jinja2 \
    gunicorn \
    python-dotenv

# The key insight: setup-environment.sh makes 'tito' command available
# We need to add the bin/ directory to PATH
ENV PATH="/app/TinyTorch/bin:${PATH}"

# Also ensure Python can find the tito module
ENV PYTHONPATH="/app/TinyTorch:${PYTHONPATH}"

# Verify tito is accessible
RUN echo "=== Checking tito availability ===" && \
    ls -la /app/TinyTorch/bin/ || echo "No bin directory" && \
    find /app/TinyTorch -name "tito*" -type f && \
    echo "=== PATH: $PATH ===" && \
    echo "=== PYTHONPATH: $PYTHONPATH ==="

# Go back to /app for our API code
WORKDIR /app

# Copy API application
COPY app.py .

# Set environment variables
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

EXPOSE ${PORT}

# Run the Flask app
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--workers", "2", "--timeout", "120", "app:app"]
