# Base image for dependencies
FROM python:3.11-slim as deps

# Install system dependencies including Tk, OpenCV requirements, and FFmpeg
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-tk \
    tk-dev \
    libgl1 \
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

# Create modified requirements files without ttkthemes and pystray
RUN grep -v "ttkthemes" requirements/runtime.txt > requirements/runtime_docker.txt
RUN grep -v "pystray" requirements/graphics.txt > requirements/graphics_docker.txt

# Install wheel and setuptools first to ensure proper wheel building
RUN pip install --no-cache-dir wheel setuptools

# Install pre-dependencies
RUN cd requirements && pip install --no-cache-dir -r pre_deps.txt

# Install Python dependencies using the modified requirements files
RUN cd requirements && pip install --no-cache-dir -r runtime_docker.txt
RUN pip install --no-cache-dir -r requirements/graphics_docker.txt

# Final stage
FROM deps AS final

# Set working directory
WORKDIR /app

# Copy source code from deps stage
COPY --from=deps /app /app
COPY ComBreak/ ComBreak/
COPY ComBreakDirect/ ComBreakDirect/
COPY CLI/ CLI/
COPY GUI/ GUI/
COPY ToonamiTools/ ToonamiTools/
COPY Tools/ Tools/
COPY API/ API/
COPY *.py ./

# Create the config file
COPY example-config.py config.py

# Copy the auto-folder setup script
COPY AutoDockerFolders.py .

# Create directories
RUN mkdir -p /app/anime && \
    mkdir -p /app/bump && \
    mkdir -p /app/special_bump && \
    mkdir -p /app/commercials && \
    mkdir -p /app/working && \
    mkdir -p /data && \
    chown -R root:root /app && \
    chmod -R 755 /app && \
    chmod 1777 /app/anime && \
    chmod 1777 /app/bump && \
    chmod 1777 /app/special_bump && \
    chmod 1777 /app/commercials && \
    chmod 1777 /app/working && \
    chmod 1777 /data

# Define volumes
VOLUME ["/app/anime", "/app/bump", "/app/special_bump", "/app/commercials", "/app/working", "/data"]

# Set environment variables
ENV ANIME_FOLDER=/app/anime \
    BUMP_FOLDER=/app/bump \
    SPECIAL_BUMP_FOLDER=/app/special_bump \
    WORKING_FOLDER=/app/working \
    COMMERCIAL_FOLDER=/app/commercials \
    ENVIRONMENT=production \
    PYTHONUNBUFFERED=1 \
    DISABLE_TTK_THEMES=1 \
    CUTLESS=true

# Expose the application ports
EXPOSE 8081 8083

# Create startup script that runs ComBreakDirect setup then launches the WebUI
RUN cat <<'EOF' > /app/start.sh
#!/bin/bash
set -e

python3 AutoDockerFolders.py

python3 run_server.py &
CBD_PID=$!
trap "kill $CBD_PID 2>/dev/null" EXIT

if [ "$CUTLESS" = "true" ] || [ "$CUTLESS" = "True" ]; then
  python3 main.py --webui --docker --cutless
else
  python3 main.py --webui --docker
fi
EOF
RUN chmod +x /app/start.sh

# Command to run both ComBreakDirect setup and the WebUI
CMD ["/app/start.sh"]
