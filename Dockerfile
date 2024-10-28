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
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy only requirements files first
COPY requirements/ requirements/
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

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
    chown -R root:root /app && \
    chmod -R 755 /app && \
    chmod 1777 /app/anime && \
    chmod 1777 /app/bump && \
    chmod 1777 /app/special_bump && \
    chmod 1777 /app/working

# Define volumes
VOLUME ["/app/anime", "/app/bump", "/app/special_bump", "/app/working"]

# Set environment variables
ENV ANIME_FOLDER=/app/anime \
    BUMP_FOLDER=/app/bump \
    SPECIAL_BUMP_FOLDER=/app/special_bump \
    WORKING_FOLDER=/app/working \
    ENVIRONMENT=production \
    PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 8081

# Command to run the auto-folder setup script and the application
CMD ["sh", "-c", "python3 AutoDockerFolders.py && python3 main.py --webui --docker"]