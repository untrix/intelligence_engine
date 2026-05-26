#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${AGENT_PLATFORM_ROOT:-"$HOME/AgentPlatform"}"
IMAGE="${AGENT_PLATFORM_IMAGE:-ghcr.io/untrix/intelligence_engine:main}"
APP_ROOT="$INSTALL_ROOT/.AgentPlatform"
COMPOSE_FILE="$APP_ROOT/docker-compose.yml"
CHROME_LAUNCHER="$INSTALL_ROOT/start-agent-chrome.sh"
PLATFORM_LAUNCHER="$INSTALL_ROOT/start-agent-platform.sh"
CHROME_STOPPER="$INSTALL_ROOT/stop-agent-chrome.sh"
PLATFORM_STOPPER="$INSTALL_ROOT/stop-agent-platform.sh"

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

CDP_URL="http://127.0.0.1:9222/json/version"
USER_DATA_DIR="$APP_ROOT/chrome-debug"

is_cdp_ready() {
  curl -fsS "\$CDP_URL" >/dev/null 2>&1
}

print_manual_workaround() {
  local chrome_path="\${1:-/path/to/Google Chrome}"
  printf '%s\n' "Agent Chrome did not start automatically."
  printf '%s\n' ""
  printf '%s\n' "Manual workaround:"
  printf '%s\n' "1. Locate Google Chrome on this Mac."
  printf '%s\n' "2. Run this command, replacing the Chrome path if needed:"
  printf '%s\n' ""
  printf '   "%s" \\\\\n' "\$chrome_path"
  printf '%s\n' '     --remote-debugging-address=127.0.0.1 \'
  printf '%s\n' '     --remote-debugging-port=9222 \'
  printf '%s\n' '     --user-data-dir="$APP_ROOT/chrome-debug" \'
  printf '%s\n' '     --new-window \'
  printf '%s\n' '     >/dev/null 2>&1 &'
  printf '%s\n' ""
  printf '%s\n' "If Chrome is installed in a custom location, rerun this helper with:"
  printf '%s\n' ""
  printf '%s\n' '   AGENT_CHROME_PATH="/path/to/Google Chrome" "$CHROME_LAUNCHER"'
}

find_chrome() {
  local candidates=(
    "\${AGENT_CHROME_PATH:-}"
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    "\$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"
    "\$HOME/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"
  )

  local candidate
  for candidate in "\${candidates[@]}"; do
    if [ -n "\$candidate" ] && [ -x "\$candidate" ]; then
      printf '%s\n' "\$candidate"
      return 0
    fi
  done

  if command -v mdfind >/dev/null 2>&1; then
    local app_path
    app_path="\$(mdfind "kMDItemCFBundleIdentifier == 'com.google.Chrome'" 2>/dev/null | head -n 1 || true)"
    if [ -n "\$app_path" ] && [ -x "\$app_path/Contents/MacOS/Google Chrome" ]; then
      printf '%s\n' "\$app_path/Contents/MacOS/Google Chrome"
      return 0
    fi
  fi

  return 1
}

if is_cdp_ready; then
  echo "Agent Chrome is already running."
  exit 0
fi

CHROME_BIN="\$(find_chrome || true)"
if [ -z "\$CHROME_BIN" ]; then
  echo "Could not find Google Chrome automatically." >&2
  print_manual_workaround "/path/to/Google Chrome" >&2
  exit 1
fi

"\$CHROME_BIN" \\
  --remote-debugging-address=127.0.0.1 \\
  --remote-debugging-port=9222 \\
  --user-data-dir="\$USER_DATA_DIR" \\
  --new-window \\
  >/dev/null 2>&1 &

for _ in {1..20}; do
  if is_cdp_ready; then
    echo "Agent Chrome started in the background."
    exit 0
  fi
  sleep 0.5
done

print_manual_workaround "\$CHROME_BIN" >&2
exit 1
SH

chmod +x "$CHROME_LAUNCHER"

cat > "$PLATFORM_LAUNCHER" <<SH
#!/usr/bin/env bash
set -euo pipefail

docker compose -f "$COMPOSE_FILE" up -d

echo "Agent Platform started. Open http://localhost:8001"
SH

chmod +x "$PLATFORM_LAUNCHER"

cat > "$CHROME_STOPPER" <<SH
#!/usr/bin/env bash
set -euo pipefail

if pgrep -f "$APP_ROOT/chrome-debug" >/dev/null 2>&1; then
  pkill -f "$APP_ROOT/chrome-debug" >/dev/null 2>&1 || true
  echo "Agent Chrome stopped."
else
  echo "Agent Chrome is not running."
fi
SH

chmod +x "$CHROME_STOPPER"

cat > "$PLATFORM_STOPPER" <<SH
#!/usr/bin/env bash
set -euo pipefail

docker compose -f "$COMPOSE_FILE" down

echo "Agent Platform stopped."
SH

chmod +x "$PLATFORM_STOPPER"

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

To stop Agent Platform:
   "$PLATFORM_STOPPER"

To stop Agent Chrome:
   "$CHROME_STOPPER"

By default, this install uses Docker image:
  $IMAGE

To install a different published image tag, set AGENT_PLATFORM_IMAGE before
running this installer. Example:
  AGENT_PLATFORM_IMAGE=ghcr.io/untrix/intelligence_engine:v0.1
EOF
