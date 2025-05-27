# Base image for dependencies
FROM python:3.11-slim as deps

# Install system dependencies including Tk, OpenCV requirements, and FFmpeg
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
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy only requirements files first
COPY requirements/ requirements/
COPY requirements.txt .

# Create a modified requirements file without ttkthemes
RUN grep -v "ttkthemes" requirements/runtime.txt > requirements/runtime_docker.txt

# Install wheel and setuptools first to ensure proper wheel building
RUN pip install --no-cache-dir wheel setuptools

# Install pre-dependencies
RUN cd requirements && pip install --no-cache-dir -r pre_deps.txt

# Install Python dependencies using the modified requirements file
RUN cd requirements && pip install --no-cache-dir -r runtime_docker.txt
RUN pip install --no-cache-dir -r requirements/graphics.txt

# Final stage
FROM deps AS final

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
    DISABLE_TTK_THEMES=1 \
    CUTLESS=true

# Expose the application port
EXPOSE 8081

# Create startup script that checks for Cutless environment variable
RUN echo '#!/bin/bash\npython3 AutoDockerFolders.py\nif [ "$CUTLESS" = "true" ] || [ "$CUTLESS" = "True" ]; then\n  python3 main.py --webui --docker --cutless\nelse\n  python3 main.py --webui --docker\nfi' > /app/start.sh && \
    chmod +x /app/start.sh

# Command to run the startup script
CMD ["/app/start.sh"]