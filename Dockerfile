FROM continuumio/miniconda3

# Set the working directory in the container
WORKDIR /app

# Install pandas using conda
RUN conda install pandas

# Install any other system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3-tk \
    tk-dev \
    tcl-dev \
    libx11-6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy your application code
COPY . /app

# Install the rest of your Python dependencies with pip
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV ANIME_FOLDER="/app/anime"
ENV BUMP_FOLDER="/app/bump"
ENV SPECIAL_BUMP_FOLDER="/app/special_bump"
ENV WORKING_FOLDER="/app/working"

# Expose port
EXPOSE 8081

CMD ["sh", "-c", "python AutoDockerFolders.py && python main.py --webui"]
