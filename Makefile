.PHONY: setup compile sync install deps dev run clean chrome-debug chrome-debug-check migrate docker-build docker-build-ghcr docker-push-ghcr docker-release-ghcr docker-up docker-down docker-logs

PYTHON := python3.13
VENV := .venv
VENV_BIN := $(VENV)/bin
UV := $(VENV_BIN)/uv
LOCKFILE := requirements_mac.lock
UV_CMD := $(if $(wildcard $(UV)),$(UV),uv)

PROJECT_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
-include $(PROJECT_ROOT)/.env
INTELLIGENCE_ENGINE_WORKSPACE_ROOT ?= $(PROJECT_ROOT)
INTELLIGENCE_ENGINE_HOME_DIR ?= $(INTELLIGENCE_ENGINE_WORKSPACE_ROOT)
INTELLIGENCE_ENGINE_DATA_DIR ?= $(PROJECT_ROOT)/data
AGENT_PLATFORM_IMAGE ?= agent-platform:latest
GHCR_IMAGE ?= ghcr.io/untrix/intelligence_engine
GHCR_TAG ?= main
CHROME ?= "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEBUG_PORT ?= 9222
CHROME_PROFILE ?= Default
CHROME_USER_DATA_DIR ?= $(INTELLIGENCE_ENGINE_DATA_DIR)/chrome-debug

setup:
	@test -x $(VENV_BIN)/python || $(PYTHON) -m venv --prompt ie $(VENV)

compile: setup
	$(UV_CMD) pip compile pyproject.toml -o $(LOCKFILE)

sync: setup
	$(UV_CMD) pip sync $(LOCKFILE)

install: sync

deps: compile sync

dev:
	$(VENV_BIN)/uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

run:
	$(VENV_BIN)/uvicorn app.main:app --host 0.0.0.0 --port 8001

migrate:
	$(VENV_BIN)/alembic upgrade head

docker-build:
	docker build -t $(AGENT_PLATFORM_IMAGE) .

docker-build-ghcr:
	docker build -t $(GHCR_IMAGE):$(GHCR_TAG) .

docker-push-ghcr:
	docker push $(GHCR_IMAGE):$(GHCR_TAG)

docker-release-ghcr: docker-build-ghcr docker-push-ghcr

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f agent-platform

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache

chrome-debug:
	@mkdir -p "$(CHROME_USER_DATA_DIR)"
	$(CHROME) \
		--user-data-dir="$(CHROME_USER_DATA_DIR)" \
		--remote-debugging-port=$(DEBUG_PORT) \
		--remote-debugging-address=127.0.0.1 \
		--profile-directory="$(CHROME_PROFILE)"

chrome-debug-check:
	@echo "Listeners on port $(DEBUG_PORT):"
	@lsof -nP -iTCP:$(DEBUG_PORT) -sTCP:LISTEN 2>/dev/null || true
	@echo ""
	@curl -fsS "http://127.0.0.1:$(DEBUG_PORT)/json/version" && echo "" || ( \
		echo ""; \
		echo "Failed to reach http://127.0.0.1:$(DEBUG_PORT)/json/version"; \
		echo "→ Run: make chrome-debug"; \
		exit 1 \
	)
