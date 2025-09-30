# Base image: slim Python
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y     build-essential     python3-dev     git     curl     && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt requirements.txt
COPY requirements-dev.txt requirements-dev.txt

# Install dependencies
RUN pip install --upgrade pip &&     pip install -r requirements.txt &&     pip install -r requirements-dev.txt

# Default command
CMD ["/bin/bash"]
