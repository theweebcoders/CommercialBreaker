# Base image for dependencies
FROM python:3.11-slim as deps

# Install system dependencies including Tk, OpenCV requirements, FFmpeg, and Redis
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-tk \
    tk-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    ffmpeg \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy only requirements files first
COPY requirements/ requirements/
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Redis Python client
RUN pip install --no-cache-dir redis

# Final stage
FROM deps as final

# Set working directory
WORKDIR /app

# Copy source code from deps stage
COPY --from=deps /app /app
COPY ComBreak/ ComBreak/
COPY CLI/ CLI/
COPY GUI/ GUI/
COPY ToonamiTools/ ToonamiTools/
COPY Tools/ Tools/
COPY *.py ./

# Create the config file
COPY example-config.py config.py

# Copy the auto-folder setup script
COPY AutoDockerFolders.py .

# Create directories
RUN mkdir -p /app/anime && \
    mkdir -p /app/bump && \
    mkdir -p /app/special_bump && \
    mkdir -p /app/working && \
    mkdir -p /data && \
    chown -R root:root /app && \
    chmod -R 755 /app && \
    chmod 1777 /app/anime && \
    chmod 1777 /app/bump && \
    chmod 1777 /app/special_bump && \
    chmod 1777 /app/working && \
    chmod 1777 /data

# Define volumes
VOLUME ["/app/anime", "/app/bump", "/app/special_bump", "/app/working", "/data"]

# Set environment variables
ENV ANIME_FOLDER=/app/anime \
    BUMP_FOLDER=/app/bump \
    SPECIAL_BUMP_FOLDER=/app/special_bump \
    WORKING_FOLDER=/app/working \
    ENVIRONMENT=production \
    PYTHONUNBUFFERED=1 \
    REDIS_HOST=localhost \
    REDIS_PORT=6379

# Expose the ports
EXPOSE 8081 6379

# Create startup script
RUN echo '#!/bin/bash\nservice redis-server start\npython3 AutoDockerFolders.py\npython3 main.py --webui --docker' > /app/start.sh && \
    chmod +x /app/start.sh

# Command to run the startup script
CMD ["/app/start.sh"]