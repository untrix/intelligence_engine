# **Product Requirements Document: Enterprise Agent Platform (a.k.a. AA Firewall)**

Large companies depend on internal tools, dashboards, scripts, and data workflows developed and maintained inhouse. These tools, which are software programs, require expensive technical expertise to develop and maintain. They integrate with various internal apps via APIs that can break when a third party app. is upgraded. Additionally, such tooling also incorporates its own bugs and operational assumptions which are hard to trace back and fix, especially when the key people who developed them leave. In short, traditional software tools are expensive to develop and maintain. Additionally, staff that actually use the tools are not capable of developing and fixing them because they lack the technical (programming) expertise to do so. These tasks fall onto in-house IT and Technical Operations teams, who quickly become an operational bottleneck.

The advent of AI agents provides a non-linear opportunity to solve the problems described above by replacing brittle tooling with resilient agentic workflows. For one, these workflows are much easier to write than traditional software and therefore can be developed by non-technical staff. Second, these agents can integrate with other apps via their human interfaces (UI) and therefore become agnostic to API changes. When the UX changes agents have the ability to recover in many cases, and if not, they can be fixed by non-technical staff because they are “programmed” in natural language. And since every app has a UI, virtually every app is now accessible with zero API integration effort. Even when the agent uses an API (e.g. through an MCP server) it has the intelligence to recover (in many cases) when faced with errors. Most importantly though, since agents behave like humans, all of the hitherto manual (digital) operations can now be automated. This opens up the market exponentially.

This PRD describes an **Enterprise AI Agent Platform** (the Agent platform) that securely hosts a company’s (henceforth the Company or Enterprise) agentic workflows (henceforth AI agents). AI agents running within this platform, just like any other software, are subject to the Company’s security, privacy and compliance policies. The Agent Platform must integrate with the company’s AAA (Authentication, Authorization and Access control) systems and be monitored by its security apparatus. Furthermore, integration into any company’s systems should be frictionless. This significantly helps adoption.

## **Product Features**

This product is designed around three main requirements:

1. Frictionless Integration  
   1. With company’s Authentication and Authorization systems  
   2. With other Apps and Data  
2. Easy to Use / Frictionless Adoption  
   1. Target audience is the full spectrum of staff; technical and non-technical  
   2. HR, Project managers, Finance, Sales, Business Development, Executives, Executive Assistants, non-programmer technical staff as well as programmers (software-engineers, IT, data analyst, security analyst)  
3. Enterprise Grade Security

### **Main features:**

1. Enterprise Integration  
   1. Self-Serve integration via local **Web Browser**
      1. App runs on laptop / desktop
      1. The user logs into sites they have access to
      3. **Zero integration steps**
         1. Instant SSO integration  
         2. Instant secure integration into data
         3. **Enables Bottom Up / Product Led Adoption**: Employees and CXOs try it in their personal lives and recommend it to the office.
      5. **Think of it as Cursor for non-technical work** (Or like Comet) 
      6. Equally useful to run workflows outside the enterprise
      3. Agnostic to API (or UI) changes
      5. Two versions. Centrally stored user workflows and settings for the Enterprise version.
         1. Enterprise Version:
            1. User logs into the app using their SSO credentials
            1. User's workflows, settings and runs are all stored in a central IT controlled DB. These can be inspected later for security and compliance
         2. Personal Version:
            1. All workflows and user settings are stored locally on the laptop and the user doesn't need to log into the app. This would be free and the hook for bottom-up adoption.
            2. **Note:** The PoC only implements this version.
   3. MCP Servers: The MCP ecosystem connects thousands of SaaS apps. securely to the Enterprise. The strategy is to integrate with thirdparty MCP servers that the Company either already has integrated with or is willing to do so. Per-user OAuth (e.g. for Google Workspace) is handled by the Agent Platform: tokens are stored centrally in IT-controlled infra and injected into MCP calls, so the user's identity (not a shared service account) drives every action and shows up correctly in upstream audit logs.
2. Ease of Use  
   1. Workflows in Natural Language instead of programs. These are the central unit of work.
   3. Agent "IDE": Monitors and helps the user develop natural language programs
   2. Agentic Scaffolding of workflows at runtime helps them run reliably
3. Enterprise Grade Security:
   1. The Agent Platform inherits the Company's security perimeter since users authenticate with the Company's SSO. Secure connection between MCP-Clients and MCP-Servers is a solved problem.
   2. Auth, audit, HITL, rate limiting and per-workflow scope policy are enforced by the platform, but configured and enforced by Company IT.
   3. Builtin Firewall  (Potential Future Features)
      1. Inspect prompts for compliance  
         1. Inspect chat context for prompt injection  
      2. LLM output for content compliance  
      3. Inspect tool calls  
      4. etc.

### **Workflow**

A workflow is the central unit of computation. The user defines a workflow and the platform runs it.

* A Workflow Contains  
  * Prompts (system and user):  
    * User develops these prompts  
    * Mention internal or external websites to visit as natural part of instructions
  * Tools available to use (via. MCP): User selects from available tools.  
  * Agent Runtime (see below)  
  * Uploaded Files
* A prompt builder helps user build a good prompt  
  * A “prompt compiler” rewrites a user’s prompt into detailed step-by-step instructions suitable for an agent  
* Run on demand or automatically  
  * Chat threads are viewable and interruptible
  * Chat threads are resumable  
* Agent Runtime: Defines how a workflow runs, including single-pass execution, tool-calling loops, multiple cooperating agents, and related patterns like Memory.
   The simplest Runtime Algorithm is “Single-Turn + Multiple Toolcalls”. There is only one agent. The workflow stops after the LLM returns a response that’s not a toolcall. Usually the LLM will call multiple tools (e.g. navigate webpages, search the web etc.) and finish its task before it generates a response. This works in a lot of use-cases. There are more complex Runtime Algorithms consisting of multiple cooperating agents with specific roles. For e.g. there could be a main orchestrator, a planner, a verifier and a summarizer implementing the ReAct pattern. Then there could be Runtime Algorithms implementing specific algorithms such as Montecarlo Tree Search (MCTS). Some Runtime Algorithms may store and retrieve memory and learnt skills. These will be maintained by Agent Platform team.
* Workflows are stored in a central database against the username.

### **Competition**

Though I haven’t conducted an exhaustive review of competition, one can expect a fair amount of competition in this area. Claude Cowork, Hermes, OpenClaw, Perplexity / Comet, Cursor and several other Agent Harness products come to mind. So far, these products demand a high level of technical skillset on part of the end-user. Therefore our product strategy will have to focus on expanding the target user base by making the product extremely easy to install, use, integrate and secure - the iPhone of agent apps. This sentiment raised ideas like local-browser based integration, the workflow builder & compiler concept and inbuilt-firewall and autobuilding workflow GUI.


#### **Unresolved Issues**
1. Headless deployment for the enterprise (but this may not be necessary)  
2. Browser Integration:
   1. Clunky: A separate copy of Chrome browser needs to be started in develper mode (make chrome-debug). This is a clunky user experience and needs to be fixed.
   3. Unstable: The Google Chrome CDP (Chrome Dev Tools) API is unstable because Google can change or take away the functionality at any time. A more reliable solution is neeed. Cloudflare's Browser Run MCP is an option but does not fully replace the rich and secure integration exposed by Chrome Deve Tools (CDP). Bundling a browser along with the app like Perplexity and Cursor do is a possible solution.
   4. Works reliably for only reading. For writing / editing, "Computer Use" tool is needed, which is expensive, slow and unreliable.
3. MCP Integration can be Brittle:
   Integration via. thirdparty MCP servers such as Zapier and Cloudflare may appear like a solved problem, however, since they are brittle since they depend on traditional software APIs
