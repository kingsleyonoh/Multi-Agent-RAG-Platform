#!/usr/bin/env bash
# Multi-Agent RAG Platform — Production Deploy Script
# Usage: ./scripts/deploy.sh [remote-host]
#
# Deploys via SSH: pull → build → migrate → restart
# Requires: docker, docker compose, git

set -e

REMOTE="${1:-}"
COMPOSE_FILE="docker-compose.prod.yml"
APP_DIR="/opt/rag-platform"

echo "=== Multi-Agent RAG Platform — Deploy ==="

if [ -n "$REMOTE" ]; then
    echo "Deploying to remote: $REMOTE"
    ssh "$REMOTE" "cd $APP_DIR && git pull origin main && docker compose -f $COMPOSE_FILE build && docker compose -f $COMPOSE_FILE up -d"
else
    echo "Deploying locally..."
    git pull origin main
    docker compose -f "$COMPOSE_FILE" build
    docker compose -f "$COMPOSE_FILE" up -d
fi

echo "Waiting for health check..."
sleep 10

# Verify deployment
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null || echo "000")

if [ "$HEALTH_STATUS" = "200" ]; then
    echo "✅ Deployment successful — health check passed"
else
    echo "⚠️  Health check returned $HEALTH_STATUS — check logs with: docker compose -f $COMPOSE_FILE logs app"
    exit 1
fi
