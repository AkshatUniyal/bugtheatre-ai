# Docker Port Mismatch

## Case Details
Language/framework: Node.js, Docker
Environment: Local Docker Compose

## Actual Behavior
Container starts, but the service is unreachable from host.

## Expected Behavior
Opening `localhost:8080` should reach the app.

## Logs
Server listening on port 3000
docker compose ps shows 0.0.0.0:8080->8080/tcp

## Dockerfile
```dockerfile
EXPOSE 8080
CMD ["npm", "start"]
```

## docker-compose.yml
```yaml
services:
  web:
    ports:
      - "8080:8080"
```
