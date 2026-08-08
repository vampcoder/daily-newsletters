# Use official slim Python 3.11 image as base
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logging stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application script
COPY main.py .

# ==============================================================================
# VOLUME MOUNT INSTRUCTION:
# DO NOT copy credentials.json or token.json into this image.
# Mount them as read-write files at runtime using Docker volume mounts:
#   -v /path/to/credentials.json:/app/credentials.json
#   -v /path/to/token.json:/app/token.json
# ==============================================================================

# Run main.py with unbuffered output (-u) for continuous live Docker logs
CMD ["python", "-u", "main.py"]
