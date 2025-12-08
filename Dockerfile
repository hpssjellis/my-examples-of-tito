# --- Dockerfile for TinyTorch API with Proper Installation ---

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/venv"

# Upgrade pip in virtual environment
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy and install Python requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Clone TinyTorch repository
RUN git clone https://github.com/MLSysBook/TinyTorch.git /app/TinyTorch

# Change to TinyTorch directory and set it up
WORKDIR /app/TinyTorch

# The setup.sh script creates a virtual environment, but we want to use our existing one
# So we'll manually install what setup.sh would do
RUN pip install --no-cache-dir \
    pytest \
    jupytext \
    pyyaml \
    rich \
    matplotlib \
    nbformat \
    nbconvert \
    ipykernel

# Install TinyTorch package itself if there's a setup.py or pyproject.toml
RUN if [ -f "setup.py" ]; then pip install -e .; \
    elif [ -f "pyproject.toml" ]; then pip install -e .; \
    else echo "No setup.py or pyproject.toml found - TinyTorch may be CLI-only"; fi

# Check if tito CLI exists in the repo and make it accessible
RUN if [ -f "bin/tito" ]; then \
        chmod +x bin/tito && \
        ln -s /app/TinyTorch/bin/tito /app/venv/bin/tito; \
    elif [ -f "tito" ]; then \
        chmod +x tito && \
        ln -s /app/TinyTorch/tito /app/venv/bin/tito; \
    elif [ -f "cli/tito" ]; then \
        chmod +x cli/tito && \
        ln -s /app/TinyTorch/cli/tito /app/venv/bin/tito; \
    fi

# Add TinyTorch to PYTHONPATH so Python can find the tito module
ENV PYTHONPATH="/app/TinyTorch:${PYTHONPATH}"

# Go back to app directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/workspace /app/workspace/notebooks /app/workspace/assignments
RUN mkdir -p /app/tinytorch /app/tinytorch/core /app/modules
RUN mkdir -p /tmp/notebooks_upload /tmp/notebooks_processed /tmp/tinytorch_workspace

# Copy application files
COPY app.py .

# Verify installations
RUN echo "=== Checking Python and pip ===" && \
    which python && python --version && \
    which pip && pip --version

RUN echo "=== Checking for tito ===" && \
    (which tito && echo "tito found in PATH" || echo "tito not in PATH") && \
    (python -c "import tito" 2>/dev/null && echo "tito module importable" || echo "tito module not importable") && \
    ls -la /app/TinyTorch/

RUN echo "=== Installed packages ===" && \
    pip list | grep -E "(pytest|jupytext|rich|torch|numpy)"

# Set environment variables
ENV PORT=10000
ENV PYTHONUNBUFFERED=1
ENV TINYTORCH_HOME=/app/TinyTorch

EXPOSE ${PORT}

# Use exec form to ensure proper signal handling
CMD ["/app/venv/bin/gunicorn", "--bind", "0.0.0.0:10000", "--workers", "2", "--timeout", "120", "app:app"]
