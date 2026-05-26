# Getting Started with the Agent Platform (Intelligence Engine)

## Prerequisites

- Runs on Mac only
- Google Chrome
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- LLM API Key (OpenAI preferred)
- Optional but preferable: Zapier MCP Server URL and token

## Installation

THe product has two parts:
- Agent Platform: A python app that either runs within docker
- Agent Chrome: An instance of your Chrome browser (which you should have already installed)
    - Looks and feels the same as the main instance - even the Dock bar icons are the identical. That's annoying, but this is a PoC :D

Optional: To cleanup a previous install, stop the docker container and Agent Chrome and then delete the `~/AgentPlatform` folder.

Run the Mac setup script from this repository URL:

```bash
curl -fsSL https://raw.githubusercontent.com/untrix/intelligence_engine/main/scripts/install-agent-platform-mac.sh | bash
```

Run the following scripts to start Agent Chrome in the background and then start the app container:

```bash
~/AgentPlatform/start-agent-chrome.sh
~/AgentPlatform/start-agent-platform.sh
```

Open http://localhost:8001 in any browser (including Agent Chrome)

To stop them in the future:

```bash
~/AgentPlatform/stop-agent-platform.sh
~/AgentPlatform/stop-agent-chrome.sh
```

### Setup Agent Chrome
- Once Agent Chrome is up, you can sign into a Chrome profile to make things easier, but you don't have to. 
- However, this is your integration point into authenticated apps / websites. Therefore you should log into any apps / websites that you want the LLM to have access to - e.g. JIRA, Confluence, LinkedIn, Workday, Google Docs etc.
- This is the full Chrome web-browser that you installed and therefore is not limited in capability.
- This is how we integrate into the Company's systems with zero IT effort and yet in full compliance with the company’s existing security controls.

### Setup the app
- Open [http://localhost:8001](http://localhost:8001) in any browser (including Agent Chrome)
- Go to **Settings** and setup at least one LLM API Key (OpenAI works reliably).
- Under settings also, setup default LLM - prefer to use the most powerful one you have available (I use gpt-5.5). The choice will impact the quality of runs.
- If you have a Zapier MCP Server URL and token, then set those up too. Without this you won't be able to use Zapier of course.


## Quick start Sample Workflows

Two sample workflows are available to get you started.

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

### Creating New Workflows
- You can define new workflows as well from the Workflows page.
- Local file paths resolve against ~/AgentPlatform/workspace (docker setup) and against the repository root (developer setup)