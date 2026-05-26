#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${AGENT_PLATFORM_ROOT:-"$HOME/AgentPlatform"}"
IMAGE="${AGENT_PLATFORM_IMAGE:-ghcr.io/untrix/intelligence_engine:dev}"
APP_ROOT="$INSTALL_ROOT/.AgentPlatform"
COMPOSE_FILE="$APP_ROOT/docker-compose.yml"
CHROME_LAUNCHER="$INSTALL_ROOT/start-agent-chrome.sh"
PLATFORM_LAUNCHER="$INSTALL_ROOT/start-agent-platform.sh"

mkdir -p "$APP_ROOT/data"
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
      - "$APP_ROOT/data:/app/data"
      - "$INSTALL_ROOT/workspace:/workspace:ro"
      - "$INSTALL_ROOT/workspace/.AgentPlatform:/workspace/.AgentPlatform:rw"
YAML

cat > "$CHROME_LAUNCHER" <<SH
#!/usr/bin/env bash
set -euo pipefail

/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
  --remote-debugging-address=127.0.0.1 \\
  --remote-debugging-port=9222 \\
  --user-data-dir="$APP_ROOT/chrome-debug" \\
  --new-window \\
  >/dev/null 2>&1 &

echo "Agent Chrome started in the background."
SH

chmod +x "$CHROME_LAUNCHER"

cat > "$PLATFORM_LAUNCHER" <<SH
#!/usr/bin/env bash
set -euo pipefail

docker compose -f "$COMPOSE_FILE" up -d

echo "Agent Platform started. Open http://localhost:8001"
SH

chmod +x "$PLATFORM_LAUNCHER"

cat <<EOF
Agent Platform folders are ready under:
  $INSTALL_ROOT

Docker Compose file:
  $COMPOSE_FILE

1. Launch host Agent Chrome:
   "$CHROME_LAUNCHER"

2. Start Agent Platform:
   "$PLATFORM_LAUNCHER"

3. Open:
   http://localhost:8001

By default, this install uses Docker image:
  $IMAGE

To install a different published image tag, set AGENT_PLATFORM_IMAGE before
running this installer. Example:
  AGENT_PLATFORM_IMAGE=ghcr.io/untrix/intelligence_engine:v0.1
EOF
