# Agent Platform (Intelligence Engine)

LLM agents platform for developing and hosting enterprise agentic workflows.

Product context and requirements: [docs/Intelligence Engine.md](docs/Intelligence%20Engine.md).
Technical architecture: [docs/Technical Design Document.md](docs/Technical%20Design%20Document.md).

## Prerequisites

- Runs on Mac only
- Google Chrome (for local-browser agent tools via CDP)
- LLM API Key (OpenAI preferred)
- Optional but preferrable: Zapier MCP Server URL and token
- Non Developers - Install via Docker
    - Docker Desktop
- Developers - Clone the Repo
    - Python 3.13
    - Optional: `uv` on your `PATH` for the first `make compile` before `uv` is installed into the virtual environment

## First-time setup

```bash
make setup
source .venv/bin/activate   # shell prompt shows (ie)
make sync
make chrome-debug   # launches a new copy of Chrome Browser distinct from the one already running. In this browser, log into your google account at profile level or at least into gmail.
make dev
```

Open [http://localhost:8001](http://localhost:8001) preferably in the same browser you just opened and configure API keys under **Settings**.

## Docker quick start (app container + host Chrome)

Option A runs only the Agent Platform app in Docker. Agent Chrome remains a normal Mac Chrome window, so users can browse and sign in natively while the container connects to Chrome through CDP.

For an end-user style install, run the Mac setup script from this repository URL:

```bash
curl -fsSL https://raw.githubusercontent.com/untrix/intelligence_engine/dev/scripts/install-agent-platform-mac.sh | bash
```

The script creates:

- `~/AgentPlatform/data` for app state
- `~/AgentPlatform/workspace` for files visible to workflow local-file tools
- `~/AgentPlatform/workspace/.AgentPlatform` as the app-managed writable workspace folder

For local development from this checkout:

```bash
make chrome-debug
make docker-up
```

Then open [http://localhost:8001](http://localhost:8001). In Docker, **Settings** should use `http://host.docker.internal:9222` for Chrome CDP; the app resolves that Docker host alias to the local bridge IP before connecting because Chrome rejects non-localhost Host headers. Do not expose Chrome CDP (`9222`) publicly.

## Quick start (sample workflows)

On first startup the app installs bundled sample workflows (see `[app/seed/sample_workflows/](app/seed/sample_workflows/)`). Sample job and candidate files live under `[.AgentPlatform/Sample Data/](.AgentPlatform/Sample%20Data/)`.

1. Open **Workflows** — you should see **Job Candidate Review** and **Submit Candidate Review (Needs MCP Key)** with a **Sample** badge.
2. Click **Run** on the **Job Candidate Review** workflow; sample runs pre-fill `candidate_name`, `job_files`, and `candidate_files` (defaults: `Jon Stewart`, `./.AgentPlatform/Sample Data/Job Files`, `./.AgentPlatform/Sample Data/Jon Stewart`).
3. Open the run under **Runs** and watch the **Result** tab when the run finishes. You can see and resume a run in the Full Thread tab (hit refresh / auto refresh if the thread is still active).

**Job Candidate Review** uses local file and browser tools only. **Submit Candidate Review (Needs MCP Key)** also enables Zapier Agentic meta-tools to submit the review (e.g. to a spreadsheet) — configure Zapier on **Integrations** before running. You will need to provide your zapier URL and token.

Paths resolve against the configured workspace root (`INTELLIGENCE_ENGINE_WORKSPACE_ROOT`). `INTELLIGENCE_ENGINE_HOME_DIR` remains supported as a legacy alias.

If you delete a sample workflow, use **Install sample workflows** on the Workflows page to restore only what is missing (your edits to existing samples are kept).

## Zapier MCP (optional)

Connect Zapier’s **Agentic** MCP server apps via meta-tools (`discover_zapier_actions`, `execute_zapier_write_action`, etc.). Enable at least Google Sheets read and write and Google Drive read actions. These are needed for the "Submit Candidate Review (Needs MCP Key)" workflow.

1. Create a server and API token at [mcp.zapier.com](https://mcp.zapier.com).
2. Open **Integrations** → **MCP Tools — Zapier**, paste the server URL and token, **Test connection**, then **Save**.
3. Edit a workflow and enable **Zapier MCP (Agentic)** tools (off by default).
4. In the workflow prompt, tell the agent when to use Zapier.

**Security:** BYOK only — never commit your token. Each MCP tool call consumes Zapier task quota (~2 tasks per call). Tool inputs/outputs are stored in run transcripts.

## Tech stack


| Layer       | Technologies                                                                                         |
| ----------- | ---------------------------------------------------------------------------------------------------- |
| UI          | FastAPI + Jinja2, HTMX 2.0.4, Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Python `markdown`             |
| Backend     | Python 3.13, Uvicorn, pydantic-settings, python-multipart, aiofiles                                  |
| Persistence | SQLite (WAL), SQLAlchemy async, aiosqlite, Alembic                                                   |
| LLMs        | openai, anthropic, google-generativeai, boto3 (Bedrock)                                              |
| Agent tools | Playwright (CDP-first), httpx, beautifulsoup4, ddgs, pypdf, python-docx, chevron, MCP client (`mcp`) |


## Local browser (agent Chrome)

Agents browse authenticated sites via a dedicated Chrome instance, separate from your everyday browser:

```bash
make chrome-debug          # launch agent Chrome on 127.0.0.1:9222
make chrome-debug-check    # verify CDP is listening
```

Sign in to sites once inside the agent Chrome window; sessions persist in `./data/chrome-debug` for local development.

Configure the CDP URL in **Settings** (local default: `http://127.0.0.1:9222`; Docker default: `http://host.docker.internal:9222`).

## Dependency management

Direct dependencies live in `[pyproject.toml](pyproject.toml)`. The pinned macOS lockfile is `[requirements_mac.lock](requirements_mac.lock)`, generated by `uv pip compile` (do not edit by hand).

```bash
make compile   # regenerate lockfile after editing pyproject.toml
make sync      # install into .venv
make deps      # compile + sync
```

## Makefile commands


| Command                   | Description                                     |
| ------------------------- | ----------------------------------------------- |
| `make setup`              | Create `.venv` with Python 3.13 and prompt `ie` |
| `make sync`               | Install packages from `requirements_mac.lock`   |
| `make dev`                | Run Uvicorn with auto-reload on port 8001       |
| `make run`                | Run Uvicorn without reload                      |
| `make migrate`            | Apply Alembic migrations                        |
| `make chrome-debug`       | Launch agent Chrome with remote debugging       |
| `make chrome-debug-check` | Verify CDP endpoint responds                    |
| `make docker-build`       | Build the app container image                   |
| `make docker-up`          | Start the app container with Docker Compose     |
| `make docker-down`        | Stop the Docker Compose stack                   |
| `make docker-logs`        | Follow app container logs                       |


## PoC scope

**Included:** personal (local) version — no SSO, single-user, all data on disk.

**Excluded:** SSO/oauth2client, gspread, bespoke per-service integrations, production image publishing.

## Environment variables

Copy `[.env.example](.env.example)` to `.env`. All settings use the `INTELLIGENCE_ENGINE_` prefix (e.g. `INTELLIGENCE_ENGINE_DATA_DIR=./data`).