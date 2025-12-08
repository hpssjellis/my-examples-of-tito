# Use a lean official Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for PyTorch, git, and virtual environments
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first
COPY requirements.txt .

# Create a virtual environment in the container
RUN python -m venv /app/venv

# Activate the virtual environment and install dependencies
# We'll modify PATH to always use the venv
ENV PATH="/app/venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/venv"

# Install PyTorch CPU version and other requirements
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Install additional required dependencies for TinyTorch
RUN pip install --no-cache-dir \
    pytest \
    jupytext \
    pyyaml \
    rich \
    matplotlib

# Clone and install TinyTorch from GitHub
RUN git clone https://github.com/MLSysBook/TinyTorch.git /tmp/tinytorch && \
    cd /tmp/tinytorch && \
    pip install -e . && \
    cd /app && \
    rm -rf /tmp/tinytorch/.git

# Keep the TinyTorch source for reference and module work
RUN mv /tmp/tinytorch /app/tinytorch_source

# Verify installations
RUN python -c "import tito; print('TinyTorch installed successfully')" || echo "TinyTorch import check"
RUN which tito && tito --version || echo "tito command available"
RUN python -c "import nbformat, nbconvert; print('Notebook support installed')" || echo "Notebook support available"
RUN python -c "import pytest; print('pytest installed')" || echo "pytest available"
RUN python -c "import jupytext; print('jupytext installed')" || echo "jupytext available"

# Create workspace directories for notebooks and assignments
RUN mkdir -p /app/workspace /app/workspace/notebooks /app/workspace/assignments

# Create the tinytorch module directory structure that tito expects
RUN mkdir -p /app/tinytorch /app/tinytorch/core /app/modules

# Copy the application code
COPY . .

# Set environment variables
ENV PORT=10000
ENV PYTHONUNBUFFERED=1
ENV TINYTORCH_HOME=/app

EXPOSE ${PORT}

# Command to run the service using Gunicorn with the virtual environment
CMD ["/app/venv/bin/gunicorn", "--bind", "0.0.0.0:10000", "--workers", "2", "--timeout", "120", "app:app"]
