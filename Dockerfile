# --- Dockerfile with Jupyter Integration ---

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install PyTorch and requirements
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Install Jupyter and related tools
RUN pip install jupyter jupyterlab notebook nbconvert nbformat

# Clone and install TinyTorch
RUN git clone https://github.com/MLSysBook/TinyTorch.git /tmp/tinytorch && \
    cd /tmp/tinytorch && \
    pip install . && \
    cd /app && \
    rm -rf /tmp/tinytorch

# Verify installation
RUN python -c "import tito; print('TinyTorch installed successfully')" || echo "TinyTorch import failed"

# Create directories for notebooks and workspace
RUN mkdir -p /app/notebooks /app/workspace /app/assignments

# Copy application code
COPY . .

# Environment variables
ENV PORT=10000
ENV JUPYTER_PORT=8888
ENV PYTHONPATH=/app:$PYTHONPATH

EXPOSE ${PORT} ${JUPYTER_PORT}

# Use a startup script to run both Flask and Jupyter
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
