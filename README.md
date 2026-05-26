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

## Installation
Two Parts:
- Agent Platform: A python app that either runs either directly on your laptop (developer setup) or as a docker container (docker setup).
- Agent Chrome: A second instance of your Chrome browser (which you have already installed).
    - Looks and feels the same as the main instance - even the Dock bar icons are the identical. This is a PoC :)

### Option 1: Run inside Docker (recommended)

- You need to have Docker Desktop
- You need to have Google Chrome
- The Agent Platform Python app runs as a docker container
- A separate copy of chrome (Agent Chrome) runs on your Mac and the Agent Platform app talks to it. 

Optional: To cleanup a previous install, stop the docker container, Agent Chrome and delete the `~/AgentPlatform` folder.

Run the Mac setup script from this repository URL:

```bash
curl -fsSL https://raw.githubusercontent.com/untrix/intelligence_engine/main/scripts/install-agent-platform-mac.sh | bash
```

Run the following scripts to start Agent Chrome in the background and then start the app container:

```bash
~/AgentPlatform/start-agent-chrome.sh
~/AgentPlatform/start-agent-platform.sh
```

Open http://localhost:8001 in any browser (including the Agent Browser)

To stop them in the future:

```bash
~/AgentPlatform/stop-agent-platform.sh
~/AgentPlatform/stop-agent-chrome.sh
```

### Setup Agent Chrome
- Once Agent Chrome is up, you can sign into a Chrome profiile to make things easier, but you don't have to. 
- However, this is your integration point into authenticated apps / websites. Therefore you should log into any apps / websites that you want the LLM to have access to - e.g. JIRA, Confluence, LinkedIn, Workday, Google Docs etc.
- This is the full Chrome web-browser that you installed and therefore is is not limited in capability.
- This is how you integrate into your Company with zero effort from IT, but still relying on the company’s existing security controls.

### Setup the app
- Open [http://localhost:8001](http://localhost:8001) in any browser (including the Agent Browser)
- Go to **Settings** and setup at least one LLM API Key (OpenAI works reliably).
- Under settings also, setup default LLM - prefer to use the most powerful one you have available (I use gpt-5.5). The choice will impact the quality of runs.
- If you have a Zapier MCP Server URL and token, then set those up too. Without this you won't be able to use Zapier of course.

## Quick start Sample Workflows

Try out the sample workflows after you have the app and Agent Chrome setup. Two sample workflows are available.

1. Open **Workflows** — you should see **Job Candidate Review** and **Submit Candidate Review (Needs MCP Key)** with a **Sample** badge.
2. Click **Run** on the **Job Candidate Review** workflow
3. A modal pops up with prefilled variables - `candidate_name`, `job_files`, and `candidate_files`. Just hit enter to proceed.
4. App starts executing the workflow.
3. Open the run under **Runs** and watch the chat session in the **Full Thread** tab (hit refresh / auto refresh for refreshing the thread as new messages appear).
4. If you're on Agent Browser then the workflow will open new tabs as it navigates the web. You may move to a new window or a new browser altogether if this gets annoying.
4. The **Result** tab shows the final result after the workflow is done.
5. You can resume or extend the run (chat thread) form the **Full Thread** by typing in a new request. For e.g. you could ask the LLM why it did what it did or ask it's help in getting around an error etc.
6. Hit 'Analyze Run' to get some tips on what to improve with your prompt and workflow.

**Job Candidate Review** workflow uses local file and browser tools only, hence it's the first one to try out.

**Submit Candidate Review (Needs MCP Key)** requires Zapier Agentic meta-tools, therefore it makes sense to run it only after configuring Zapier on the **Integrations** page.

### New Workflows
- You can define new workflows as well from the Workflows page.
- Local file paths resolve against ~/AgentPlatform/workspaace (docker setup) and agains the repository root (developer setup)

### Setting up Zapier MCP Connection

Connect Zapier’s Agentic MCP server apps via meta-tools (`discover_zapier_actions`, `execute_zapier_write_action`, etc.). Enable at least Google Sheets read and write and Google Drive read actions. These are needed for the **Submit Candidate Review (Needs MCP Key)** workflow.

1. Create a server and API token at [mcp.zapier.com](https://mcp.zapier.com).
2. Open **Integrations** → **MCP Tools — Zapier**, paste the server URL and token, **Test connection**, then **Save**.
3. Edit a workflow and enable **Zapier MCP (Agentic)** tools (off by default).


### Install Option 2: Developer Setup

```bash
git clone git@github.com:untrix/intelligence_engine.git
cd ./intelligence_engine
make setup
source .venv/bin/activate   # shell prompt shows (ie)
make sync
make chrome-debug   # launches a new copy of Chrome Browser distinct from the one already running. In this browser, log into all authenticated apps that you want to integrate with.
make run  # launches the Agent Platform Python app.
```

# Developer Zone


## Tech stack


| Layer       | Technologies                                                                                         |
| ----------- | ---------------------------------------------------------------------------------------------------- |
| UI          | FastAPI + Jinja2, HTMX 2.0.4, Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Python `markdown`             |
| Backend     | Python 3.13, Uvicorn, pydantic-settings, python-multipart, aiofiles                                  |
| Persistence | SQLite (WAL), SQLAlchemy async, aiosqlite, Alembic                                                   |
| LLMs        | openai, anthropic, google-generativeai, boto3 (Bedrock)                                              |
| Agent tools | Playwright (CDP-first), httpx, beautifulsoup4, ddgs, pypdf, python-docx, chevron, MCP client (`mcp`) |


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