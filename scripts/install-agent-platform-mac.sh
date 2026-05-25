#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${AGENT_PLATFORM_ROOT:-"$HOME/AgentPlatform"}"
IMAGE="${AGENT_PLATFORM_IMAGE:-ghcr.io/agent-platform/agent-platform:latest}"
COMPOSE_FILE="$INSTALL_ROOT/docker-compose.yml"

mkdir -p "$INSTALL_ROOT/data"
mkdir -p "$INSTALL_ROOT/workspace/.AgentPlatform"

cat > "$COMPOSE_FILE" <<YAML
services:
  agent-platform:
    image: $IMAGE
    ports:
      - "8001:8001"
    environment:
      INTELLIGENCE_ENGINE_HOST: 0.0.0.0
      INTELLIGENCE_ENGINE_PORT: "8001"
      INTELLIGENCE_ENGINE_DATA_DIR: /app/data
      INTELLIGENCE_ENGINE_WORKSPACE_ROOT: /workspace
      INTELLIGENCE_ENGINE_CHROME_CDP_URL: http://host.docker.internal:9222
    volumes:
      - "$INSTALL_ROOT/data:/app/data"
      - "$INSTALL_ROOT/workspace:/workspace:ro"
      - "$INSTALL_ROOT/workspace/.AgentPlatform:/workspace/.AgentPlatform:rw"
YAML

cat <<EOF
Agent Platform folders are ready under:
  $INSTALL_ROOT

Docker Compose file:
  $COMPOSE_FILE

1. Launch host Agent Chrome:
   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
     --remote-debugging-address=127.0.0.1 \\
     --remote-debugging-port=9222 \\
     --user-data-dir="$INSTALL_ROOT/chrome-debug" \\
     --new-window

2. Start Agent Platform:
   cd "$INSTALL_ROOT"
   docker compose up -d

3. Open:
   http://localhost:8001

Override the image before running this installer with:
  AGENT_PLATFORM_IMAGE=ghcr.io/<owner>/<image>:<tag>
EOF
