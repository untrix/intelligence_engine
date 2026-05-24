# **Product Requirements Document: Enterprise Agents Platform (a.k.a. AA Firewall)**

Large companies depend on internal tools, dashboards, scripts, and data workflows developed and maintained inhouse. These tools, which are software programs, require expensive technical expertise to develop and maintain. They integrate with various internal apps via APIs that can break when a third party app. is upgraded. Additionally, such tooling also incorporates its own bugs and operational assumptions which are hard to trace back and fix, especially when the key people who developed them leave. In short, traditional software tools are expensive to develop and maintain. Additionally, staff that actually use the tools are not capable of developing and fixing them because they lack the technical (programming) expertise to do so. These tasks fall onto in-house IT and Technical Operations teams, who quickly become an operational bottleneck.

The advent of AI agents provides a non-linear opportunity to solve the problems described above by replacing brittle tooling with resilient agentic workflows. For one, these workflows are much easier to write than traditional software and therefore can be developed by non-technical staff. Second, these agents can integrate with other apps via their human interfaces (UI) and therefore become agnostic to API changes. When the UX changes agents have the ability to recover in many cases, and if not, they can be fixed by non-technical staff because they are “programmed” in natural language. And since every app has a UI, virtually every app is now accessible with zero API integration effort. Even when the agent uses an API (e.g. through an MCP server) it has the intelligence to recover (in many cases) when faced with errors. Most importantly though, since agents behave like humans, all of the hitherto manual (digital) operations can now be automated. This opens up the market exponentially.

This PRD describes an **Enterprise Agentic AI Platform** (the platform) that securely hosts a company’s agentic workflows (henceforth AI agents). AI agents running within this platform, just like any other software, are subject to the company’s security, privacy and compliance policies. The platform must integrate with the company’s AAA (Authentication, Authorization and Access control) systems and be monitored by its security apparatus. Furthermore, integration into any company’s systems should be frictionless. This significantly helps adoption.

## **Product Features**

This product is designed around three main requirements:

1. Frictionless Integration  
   1. With company’s Authentication and Authorization systems  
   2. With other Apps and Data  
2. Easy to Use  
   1. Target audience is the full spectrum of staff; technical and non-technical  
   2. HR, Project managers, Finance, Sales, Business Development, Executives, Executive Assistants, non-programmer technical staff as well as programmers (software-engineers, IT, data analyst, security analyst)  
3. Builtin Firewall (Future)

### **Main features:**

1. Enterprise Integration  
   1. Self-Serve integration via a local Web Browser running on the User's machine
      1. App runs on laptop / desktop both at home (via. VPN if needed) and the office
      2. Uses local Chrome browser to fetch data from all sites and web-apps that the user has access to
      3. **Zero integration steps (**works out of the box)  
         1. Instant SSO integration  
         2. Instant secure integration into data  
         3. **Enables Bottom Up / Product Led Adoption**: Employees and CXOs try it in their personal lives and recommend it to the office.  
      4. Easy to inject Human in The Loop: non-technical people can “debug” when things go wrong  
      5. **Think of it as Cursor for non-technical work**  
      6. Equally useful to run workflows outside the enterprise
   3. Agnostic to API (or UI) changes
   5. Two versions. Centrally stored user workflows and settings for the Enterprise version.
      1. Enterprise Version:
         1. User logs into the app using their SSO credentials
         1. User's workflows, settings and runs are all stored in a central IT controlled DB. These can be inspected later for security.
      2. Personal Version:
         1. All workflows and user settings are stored locally on the laptop and the user doesn't need to log into the app. This would be free and the hook for bottom-up adoption.
         2. **Note:** The PoC only implements this version.
         3. **PoC Stretch Goal — MCP client support.** After the baseline functionality (workflows, local-browser tools, prompt builder, agent threads) is working, add an MCP client so the platform can attach to any local or remote MCP server. This unlocks the existing MCP ecosystem (filesystem, git, sqlite, search, GitHub, Linear, Slack, Google Workspace, etc.) for personal workflows immediately, and is the same client layer the Enterprise Version will use to consume the company's MCP server(s) later. Decision rationale: per-service bespoke integrations cost ~1–2 weeks each forever, while an MCP-based path costs a one-time client implementation and reduces each new integration to a server registration.
2. Ease of Use  
   1. Workflows in Natural Language: Central unit of computation.

### **Future Features (Not in this version)**

2. Advanced integration via off-the-shelf components:  
   1. MCP Server: For non-browseable data, integrate into Company’s MCP server. Company IT procures their own MCP server with all integrations they allow.  
      1. **MCP is the preferred path for all structured/API integrations in the Enterprise Version** (e.g. Google Sheets editing, Gmail, Drive, Calendar, Slack, Jira, GitHub, internal systems). Rather than building bespoke per-service code, the platform speaks MCP as a client and IT either self-hosts vetted open-source MCP servers, deploys an internal MCP gateway that fronts upstream servers, or uses a managed aggregator. Auth, audit, HITL, rate limiting and per-workflow scope policy are enforced by the platform's MCP-client middleware so they apply uniformly to every server.  
      2. Per-user OAuth (e.g. for Google Workspace) is handled by the platform: tokens are stored centrally in IT-controlled infra and injected into MCP calls, so the user's identity (not a shared service account) drives every action and shows up correctly in upstream audit logs.  
   2. Integrate into Company’s LLM gateway or LLM if they have one. Again, Company IT procures their own LLM gateway and LLM if they need it.  
3. Builtin Firewall  
   1. Inspect prompts for compliance  
      1. Inspect chat context for prompt injection  
   2. LLM output for content compliance  
   3. Inspect tool calls  
   4. Etc.  
4. Auto Built GUI  
   1. Auto build a GUI for each workflow


### **Workflow**

A workflow is the central unit of computation. The user defines a workflow and the platform runs it.

* A Workflow Contains  
  * Prompts (system and user):  
    * User develops these prompts  
    * Mention internal or external websites to visit as natural part of instructions
  * Tools available to use (via. MCP): User selects from available tools.  
  * Agent Orchestration Playbook (see below)  
  * Uploaded Files
* A prompt builder helps user build a good prompt  
  * A “prompt compiler” rewrites a user’s prompt into detailed step-by-step instructions suitable for an agent  
* Run on demand or automatically  
  * Chat threads are viewable and interruptible
  * Chat threads are resumable  
* Agent Orchestration Playbook: Defines a set of agents and how they cooperate to run a task.
The simplest playbook is “Single-Turn + Multiple Toolcalls”. There is only one agent. The workflow stops after the LLM returns a response that’s not a toolcall. Usually the LLM will call multiple tools (e.g. navigate webpages, search the web etc.) and finish its task before it generates a response. This works in a lot of use-cases. There are more complex orchestration patterns where there are multiple cooperating agents with specific roles. For e.g. there could be a main orchestrator, a planner, a verifier and a summarizer implementing the ReAct pattern. Then there could be playbooks implementing specific algorithms such as Montecarlo Tree Search (MCTS). These will be maintained by us.
* Workflows are stored in a central database against the username.

### **Competition**

Though I haven’t conducted an exhaustive review of competition, one can expect a fair amount of competition in this area. Claude Cowork, Hermes, OpenClaw come to mind. So far, these products demand quite a high level of technical skillset on part of the end-user. Therefore our product strategy will have to focus on expanding the target user base by making the product extremely easy to install, use, integrate and secure. This sentiment spawned ideas like local-browser based integration, the workflow builder & compiler concept and inbuilt-firewall and autobuilding workflow GUI.

#### **Unresolved Issues and ToDos**
1. Headless deployment for the enterprise (but this may not be necessary)  
2. Browser Integration:
   1. Clunky: A separate copy of Chrome browser needs to be started in develper mode (make chrome-debug). This needs a better long-term solution.
   3. Risky: Dependency on the chrome debug mode is risky because the functionality can be taken away at any time. A more dependable solution is neeed.
   3. Solution TBD: Bundle browser along with the app.