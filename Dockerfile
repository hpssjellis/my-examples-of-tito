# Dockerfile

# Use a lean official Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port (Render will handle mapping to its public IP)
# The default web service port on Render is often 10000 (set by the $PORT env var)
ENV PORT 10000 
EXPOSE ${PORT}

# Command to run the service using Gunicorn (a production Python web server)
# Use 0.0.0.0 and the $PORT environment variable
# Assuming the Flask/FastAPI app object is called 'app' inside app.py
CMD exec gunicorn --bind 0.0.0.0:${PORT} app:app
