# Docker Setup Guide

Complete guide for running CommercialBreaker & Toonami Tools in Docker containers.

## Quick Start

### Option 1: Pre-built Image (Recommended)

```bash
docker run -p 8081:8081 \
  -v "/path/to/your/Anime:/app/anime" \
  -v "/path/to/your/Bumps:/app/bump" \
  -v "/path/to/your/SpecialBumps:/app/special_bump" \
  -v "/path/to/your/Working:/app/working" \
  --name commercialbreaker \
  tim000x3/commercial-breaker:latest
```

### Option 2: Local Build

```bash
git clone https://github.com/theweebcoders/CommercialBreaker.git
cd CommercialBreaker
cp example.env .env
# Edit .env with your paths
docker compose up -d
```

---

## Environment Configuration

### Required .env File

Create `.env` in the project root:

```bash
# Required folder paths (absolute paths recommended)
ANIME_FOLDER=/path/to/your/anime
BUMPS_FOLDER=/path/to/your/bumps
SPECIAL_BUMPS_FOLDER=/path/to/your/special_bumps
WORKING_FOLDER=/path/to/your/working
```

### Path Requirements

**Folder paths must**:
- Use absolute paths from host system
- Point to existing directories
- Be accessible by Docker daemon
- Have appropriate read/write permissions

**Example structure**:
```
/media/anime/
├── Shows/              # → ANIME_FOLDER
├── Bumps/              # → BUMPS_FOLDER
├── SpecialBumps/       # → SPECIAL_BUMPS_FOLDER
└── Working/            # → WORKING_FOLDER
```

---

## Docker Compose Setup

### Full docker-compose.yml

```yaml
version: '3.8'

services:
  commercialbreaker:
    build: .
    # Or use pre-built image:
    # image: tim000x3/commercial-breaker:latest
    container_name: commercialbreaker
    ports:
      - "8081:8081"
    volumes:
      - "${ANIME_FOLDER}:/app/anime"
      - "${BUMPS_FOLDER}:/app/bump"
      - "${SPECIAL_BUMPS_FOLDER}:/app/special_bump"
      - "${WORKING_FOLDER}:/app/working"
      - "./data:/app/data"           # Database persistence
      - "./logs:/app/logs"           # Log persistence
    environment:
      - ANIME_FOLDER=/app/anime
      - BUMPS_FOLDER=/app/bump
      - SPECIAL_BUMPS_FOLDER=/app/special_bump
      - WORKING_FOLDER=/app/working
      - DATABASE_PATH=/app/data/Toonami.db
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Include DizqueTV
  dizquetv:
    image: vexorian/dizquetv:latest
    container_name: dizquetv
    ports:
      - "8000:8000"
    volumes:
      - "./dizquetv-config:/home/node/app/.dizquetv"
      - "${ANIME_FOLDER}:/media/anime:ro"
      - "${BUMPS_FOLDER}:/media/bumps:ro"
    restart: unless-stopped

  # Optional: Include Plex
  plex:
    image: plexinc/pms-docker:latest
    container_name: plex
    ports:
      - "32400:32400"
    volumes:
      - "./plex-config:/config"
      - "${ANIME_FOLDER}:/media/anime:ro"
    environment:
      - PLEX_CLAIM=your-claim-token
    restart: unless-stopped
```

### Minimal Setup

For just CommercialBreaker:

```yaml
version: '3.8'

services:
  commercialbreaker:
    image: tim000x3/commercial-breaker:latest
    container_name: commercialbreaker
    ports:
      - "8081:8081"
    environment:
      - ANIME_FOLDER=/app/anime
      - BUMPS_FOLDER=/app/bump
      - SPECIAL_BUMPS_FOLDER=/app/special_bump
      - WORKING_FOLDER=/app/working
    restart: unless-stopped
```

---

## Container Management

### Starting Services

```bash
# Start all services
docker compose up -d

# Start specific service
docker compose up -d commercialbreaker

# View logs
docker compose logs -f commercialbreaker

# Check status
docker compose ps
```

### Updating

```bash
# Pull latest image
docker compose pull

# Restart with new image
docker compose up -d --force-recreate

# Clean up old images
docker image prune
```

### Stopping Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (careful!)
docker compose down -v

# Force stop
docker compose kill
```

---

## Volume Mounts Explained

### Content Volumes

```yaml
volumes:
  - "${ANIME_FOLDER}:/app/anime"        # Anime collection
  - "${BUMPS_FOLDER}:/app/bump"         # Toonami bumps and transitions
  - "${SPECIAL_BUMPS_FOLDER}:/app/special_bump"  # Music videos, extras
  - "${WORKING_FOLDER}:/app/working"    # Processing workspace (read/write)
```

### Data Persistence

```yaml
volumes:
  - "./data:/app/data"                  # Database and configuration
  - "./logs:/app/logs"                  # Application logs
  - "./cache:/app/cache"                # API response cache
```

---

## Network Configuration

### Internal Communication

When running multiple containers, use internal networking:


```yaml
networks:
  default:
    name: toonami-network

services:
  commercialbreaker:
    networks:
      - default
    environment:
      - DIZQUETV_URL=http://dizquetv:8000
      - PLEX_URL=http://plex:32400

  dizquetv:
    networks:
      - default

  plex:
    networks:
      - default
```

### External Access

```yaml
services:
  commercialbreaker:
    ports:
      - "8081:8081"                     # Web interface
    # Or bind to specific interface:
    # ports:
    #   - "192.168.1.100:8081:8081"
```

---

## Security Considerations

### File Permissions

```bash
# Ensure Docker daemon can access folders
sudo chown -R 1000:1000 /path/to/anime
sudo chmod -R 755 /path/to/anime

# For working directory (needs write access)
sudo chmod -R 775 /path/to/working
```

### User Mapping

```yaml
services:
  commercialbreaker:
    user: "1000:1000"                   # Match host user
    # Or use environment variables:
    # user: "${UID}:${GID}"
```

### Read-Only Mounts

```yaml
volumes:
  - "${ANIME_FOLDER}:/app/anime:ro"     # Read-only anime
  - "${BUMPS_FOLDER}:/app/bump:ro"      # Read-only bumps
  - "${WORKING_FOLDER}:/app/working:rw" # Read-write working
```

---

## Performance Optimization

### Resource Limits

```yaml
services:
  commercialbreaker:
    mem_limit: 8g                       # Memory limit
    cpus: 4                            # CPU limit
    ulimits:
      memlock:
        soft: -1
        hard: -1
    shm_size: 2g                       # Shared memory
```

### Storage Optimization

```yaml
services:
  commercialbreaker:
    volumes:
      - type: bind
        source: "${WORKING_FOLDER}"
        target: /app/working
        bind:
          propagation: cached           # Better performance
```

### Tmpfs for Temporary Files

```yaml
services:
  commercialbreaker:
    tmpfs:
      - /tmp:size=2G,uid=1000,gid=1000
      - /app/temp:size=5G
```

---

## Health Checks and Monitoring

### Health Check Configuration

```yaml
services:
  commercialbreaker:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

### Logging Configuration

```yaml
services:
  commercialbreaker:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    # Or use external logging:
    # logging:
    #   driver: syslog
    #   options:
    #     syslog-address: "tcp://logserver:514"
```

### Monitoring Commands

```bash
# View resource usage
docker stats commercialbreaker

# Monitor logs in real-time
docker logs -f commercialbreaker

# Check health status
docker inspect --format='{{.State.Health.Status}}' commercialbreaker

# Container details
docker inspect commercialbreaker
```

---

## Troubleshooting

### Common Issues

**Container won't start**:
```bash
# Check logs
docker logs commercialbreaker

# Verify environment
docker compose config

# Test volume mounts
docker run --rm -v "${ANIME_FOLDER}:/test" alpine ls -la /test
```

**Permission denied errors**:
```bash
# Fix ownership
sudo chown -R $(id -u):$(id -g) /path/to/working

# Check SELinux/AppArmor
ls -laZ /path/to/working
```

**Memory issues**:
```bash
# Increase memory limit
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Monitor memory usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Container Shell Access

```bash
# Access running container
docker exec -it commercialbreaker /bin/bash

# Run temporary debug container
docker run --rm -it \
  -v "${ANIME_FOLDER}:/app/anime" \
  tim000x3/commercial-breaker:latest \
  /bin/bash
```

---

## Backup and Recovery

### Database Backup

```bash
# Backup database
docker cp commercialbreaker:/app/data/Toonami.db ./backup/

# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker cp commercialbreaker:/app/data/Toonami.db ./backups/Toonami_${DATE}.db
```

### Configuration Backup

```bash
# Backup entire configuration
tar -czf commercialbreaker_config_$(date +%Y%m%d).tar.gz \
  .env docker-compose.yml data/ logs/
```

### Recovery

```bash
# Stop container
docker compose down

# Restore database
cp ./backup/Toonami.db ./data/

# Restart
docker compose up -d
```

---

## Integration with External Services

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name commercialbreaker.local;

    location / {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL with Let's Encrypt

```yaml
services:
  commercialbreaker:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.commercialbreaker.rule=Host(`commercialbreaker.yourdomain.com`)"
      - "traefik.http.routers.commercialbreaker.tls.certresolver=letsencrypt"
```

---

## Development Setup

### Local Development

```yaml
services:
  commercialbreaker-dev:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app                          # Mount source code
      - "${ANIME_FOLDER}:/app/anime"
    ports:
      - "8081:8081"
      - "5678:5678"                     # Debug port
    environment:
      - FLASK_ENV=development
      - DEBUG=true
```

### Multi-Architecture Builds

```bash
# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 -t commercialbreaker:latest .

# Push multi-arch image
docker buildx build --platform linux/amd64,linux/arm64 -t user/commercialbreaker:latest --push .
```

---

## Production Deployment

### Docker Swarm

```yaml
version: '3.8'

services:
  commercialbreaker:
    image: tim000x3/commercial-breaker:latest
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    networks:
      - toonami-network
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: commercialbreaker
spec:
  replicas: 1
  selector:
    matchLabels:
      app: commercialbreaker
  template:
    metadata:
      labels:
        app: commercialbreaker
    spec:
      containers:
      - name: commercialbreaker
        image: tim000x3/commercial-breaker:latest
        ports:
        - containerPort: 8081
        volumeMounts:
        - name: anime-storage
          mountPath: /app/anime
        - name: working-storage
          mountPath: /app/working
      volumes:
      - name: anime-storage
        persistentVolumeClaim:
          claimName: anime-pvc
      - name: working-storage
        persistentVolumeClaim:
          claimName: working-pvc
```

---

For more information:
- [Configuration Reference](Configuration-Reference) - Environment variables
- [Troubleshooting](Troubleshooting) - Common issues
- [Architecture Overview](Architecture-Overview) - System design
