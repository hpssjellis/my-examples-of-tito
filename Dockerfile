# --- Dockerfile ---

# Use a lean official Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for PyTorch and other complex packages
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt .

# CRITICAL FIX: Use the --extra-index-url flag for CPU-only PyTorch
# This ensures a faster, smaller, and correct installation.
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Copy the application code and any necessary TinyTorch files (like your .py assignments)
COPY . .

# Environment variable for the port (Render injects this)
ENV PORT 10000 
EXPOSE ${PORT}

# Command to run the service using Gunicorn
# It binds to 0.0.0.0 on the port set by the hosting environment (${PORT})
# The format is 'module:app_object'
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT}", "app:app"]
