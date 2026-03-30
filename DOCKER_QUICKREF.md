# Docker Quick Reference

## Building and Running

### Build Image
```bash
docker build -t knee-oa-api:latest .
```

### Run Container (Development)
```bash
docker-compose up -d
```

### Run Container (Production)
```bash
docker run -d \
  --name knee-oa-api \
  --env-file .env \
  -p 8000:8000 \
  --restart unless-stopped \
  --cpus=1.0 \
  --memory=512m \
  knee-oa-api:latest
```

### Stop and Remove
```bash
docker-compose down
docker-compose down -v  # Also remove volumes
```

## Checking Status

### View Logs
```bash
docker logs -f knee_oa_api
docker-compose logs -f api
```

### Check Health
```bash
docker inspect --format='{{.State.Health.Status}}' knee_oa_api
```

### Execute Commands
```bash
docker exec -it knee_oa_api bash
docker exec -it knee_oa_api python -c "from app.main import app; print(app.title)"
```

## Development Workflow

### With Hot Reload (Development)
```bash
docker-compose up
```
This mounts local code for hot-reload during development.

### Without Volume Mount (Production-like)
```bash
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs knee_oa_api

# Check environment variables
docker exec knee_oa_api env | grep -E "SECRET_KEY|DATABASE_URL"
```

### Health Check Failing
```bash
# Test health endpoint manually
curl http://localhost:8000/health

# Check if app is running
docker exec knee_oa_api ps aux
```

### Database Connection Issues
```bash
# Check database container
docker logs knee_oa_db

# Test database connection
docker exec -it knee_oa_api python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://...')"
```

## Image Optimization

### Check Image Size
```bash
docker images knee-oa-api
```

### Remove Unused Images
```bash
docker image prune -a
```

### Build Specific Stage
```bash
docker build --target runtime -t knee-oa-api:latest .
```

## Security Best Practices

### Run as Non-Root User
✅ Already configured in Dockerfile (appuser)

### Use Secrets for Sensitive Data
```bash
# Create secret
echo "my-secret-key" | docker secret create secret_key -

# Use in container
docker service create --secret secret_key ...
```

### Scan for Vulnerabilities
```bash
docker scan knee-oa-api:latest
```

## Environment Variables

### Required in .env
```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://...
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
S3_BUCKET_NAME=your-bucket
```

### Optional
```bash
DEBUG=false
LOG_LEVEL=INFO
ACCESS_TOKEN_EXPIRE_MINUTES=15
```

## Multi-Stage Build Explanation

### Stage 1: Builder
- Installs all dependencies
- Creates virtual environment
- Used only during build

### Stage 2: Runtime
- Clean Python image
- Copies only virtual environment
- Runs as non-root user
- Much smaller image size

## Performance Tips

### Reduce Image Size
- Use multi-stage builds ✅
- Use slim base images ✅
- Clean apt cache ✅
- Don't copy unnecessary files (.dockerignore) ✅

### Improve Build Speed
- Copy requirements.txt first ✅
- Use Docker cache effectively ✅
- Use .dockerignore ✅

### Optimize Runtime
- Health checks ✅
- Resource limits ✅
- Logging rotation ✅

## Common Commands

### Interactive Shell
```bash
docker exec -it knee_oa_api bash
```

### Run Migrations
```bash
docker exec -it knee_oa_api alembic upgrade head
```

### Initialize Admin
```bash
docker exec -it knee_oa_api python scripts/init_admin.py
```

### Run Tests
```bash
docker exec -it knee_oa_api pytest tests/ -v
```

### Backup Database
```bash
docker exec knee_oa_db pg_dump -U neondb_owner knee_oa > backup.sql
```

### Restore Database
```bash
docker cp backup.sql knee_oa_db:/backup.sql
docker exec -i knee_oa_db psql -U neondb_owner knee_oa < /backup.sql
```

## Production Checklist

- [ ] Use production .env file
- [ ] Set DEBUG=false
- [ ] Use strong SECRET_KEY
- [ ] Enable health checks
- [ ] Set resource limits
- [ ] Configure logging rotation
- [ ] Use non-root user ✅
- [ ] Scan for vulnerabilities
- [ ] Test health endpoint
- [ ] Monitor container logs
- [ ] Set up backup strategy
- [ ] Document recovery procedures

---

**Last Updated**: March 30, 2026
