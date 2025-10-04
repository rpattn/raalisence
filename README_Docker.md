# Docker Setup for Python raalisence

This document describes how to build and run the Python version of raalisence using Docker.

## Available Dockerfiles

### 1. `Dockerfile.python` (Recommended for most use cases)
- Multi-stage build with Python 3.11 slim base
- Includes health checks and proper security practices
- Uses non-root user for security
- Includes curl for health checks

### 2. `Dockerfile.python.prod` (Production-optimized)
- Uses distroless base image for minimal attack surface
- Smaller image size
- No shell or package manager included
- Best for production deployments

## Quick Start

### Build and run with Docker Compose (Recommended)

```bash
# Build and start the service
docker-compose -f docker-compose.python.yaml up --build

# Run in background
docker-compose -f docker-compose.python.yaml up -d --build

# View logs
docker-compose -f docker-compose.python.yaml logs -f

# Stop the service
docker-compose -f docker-compose.python.yaml down
```

### Build and run manually

```bash
# Build the image
docker build -f Dockerfile.python -t raalisence-python .

# Run the container
docker run -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  raalisence-python
```

## Configuration

### Environment Variables

- `PYTHONPATH`: Set to `/app` (default)
- `RA_DB_PATH`: Path to SQLite database file (default: `/app/data/raalisence.db`)

### Volume Mounts

- `/app/data`: Directory for SQLite database files
- `/app/config.yaml`: Configuration file (read-only)

### Ports

- `8080`: HTTP server port

## Production Deployment

### Using the production Dockerfile

```bash
# Build production image
docker build -f Dockerfile.python.prod -t raalisence-python:prod .

# Run production container
docker run -p 8080:8080 \
  -v /path/to/data:/app/data \
  -v /path/to/config.yaml:/app/config.yaml:ro \
  raalisence-python:prod
```

### Health Checks

The container includes health checks that verify the service is responding:

```bash
# Check container health
docker ps

# View health check logs
docker inspect <container_id> | grep -A 10 Health
```

## Database Options

### SQLite (Default)
- Database file stored in `/app/data/raalisence.db`
- No additional setup required
- Good for development and small deployments

### PostgreSQL
- Use the provided docker-compose.yaml with PostgreSQL service
- Update config.yaml to use PostgreSQL DSN
- Better for production and high-availability deployments

## Security Considerations

1. **Non-root user**: The container runs as a non-root user (`raalisence`)
2. **Minimal base image**: Uses slim Python image or distroless for production
3. **Read-only config**: Configuration file is mounted read-only
4. **No shell access**: Production image doesn't include shell or package manager

## Troubleshooting

### Common Issues

1. **Permission denied on data directory**
   ```bash
   # Fix permissions
   sudo chown -R 1000:1000 ./data
   ```

2. **Health check failing**
   ```bash
   # Check logs
   docker logs <container_id>
   
   # Test health endpoint manually
   curl http://localhost:8080/healthz
   ```

3. **Database connection issues**
   - Verify database path in config.yaml
   - Check volume mount permissions
   - Ensure database directory exists

### Debug Mode

To run with debug logging:

```bash
docker run -p 8080:8080 \
  -e PYTHONUNBUFFERED=1 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  raalisence-python
```

## Development

### Local Development with Docker

```bash
# Build development image
docker build -f Dockerfile.python -t raalisence-python:dev .

# Run with volume mounts for live code changes
docker run -p 8080:8080 \
  -v $(pwd)/python_raalisence:/app/python_raalisence \
  -v $(pwd)/static:/app/static \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/data:/app/data \
  raalisence-python:dev
```

### Running Tests

```bash
# Run tests in container
docker run --rm \
  -v $(pwd):/app \
  -w /app \
  raalisence-python:dev \
  python -m pytest tests/
```
