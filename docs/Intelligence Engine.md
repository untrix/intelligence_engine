# Product Requirements Document: Agent Platform (a.k.a. AA Firewall)

## Problem

Large companies depend on internal tools, dashboards, scripts, and data workflows. These tools are usually built and maintained by technical teams, even when the people who use them are non-technical business users.

This creates several problems:

1. Traditional software tools are expensive to build and maintain.
2. Integrations break when internal systems or third-party apps change their APIs or user interfaces.
3. Operational knowledge gets embedded in scripts and dashboards that are hard to debug or update later.
4. The people closest to the work usually cannot fix the tools themselves, so IT and technical operations teams become bottlenecks.

## Opportunity

AI agents create an opportunity to replace brittle internal tooling with resilient agentic workflows.

Agentic workflows are easier to author than traditional software because they can be described in natural language. Non-technical staff can define or adjust them without learning to program. Agents can also interact with applications through human interfaces, which makes many workflows less dependent on brittle APIs. When an interface changes, an agent may be able to recover. If it cannot, the workflow can often be fixed by editing natural-language instructions instead of code.

This matters because every application already has a UI. In principle, any digital process that a human can perform manually can become automatable without waiting for a bespoke integration. When an agent uses an API through an MCP server, it can still apply reasoning and recovery behavior around failures instead of treating every error as a hard stop.

## Product Overview

The **Agent Platform** securely hosts agentic workflows. The same product can run in two management modes:

1. **Self-Managed:** the end user manages settings, credentials, connectors, logs, and local storage (but would still need to log into the Company SSO in order to run workflows against their work app accounts)
2. **Company-Managed:** Company IT manages or constrains settings, credentials, connector access, logs, and governance policy.

This is similar to managed browser profiles or remote device management: Chrome is still Chrome whether a user opens a personal profile or a company-managed profile, and a laptop is still the same device class whether it is personally owned or IT-managed. The difference is who configures, governs, monitors, and audits it.

Architecturally, the Agent Platform product, uses a **federated architecture with distributed runtime compute** rather than a traditional client-server enterprise app. Each Agent Platform node supplies runtime compute, whether it is a weak laptop, a powerful workstation, or a high-capacity managed worker. Other systems the platform interacts with — identity providers, SaaS apps, MCP servers, LLM gateways, internal tools — are independently governed systems in the broader federation, and each brings its own authentication, authorization, accces and audit controls.

Governance is a separate plane. In Self-Managed mode, the user governs their own node. In Company-Managed mode, Company IT governs nodes through Agent Platform Inc.'s management portal by defining policy, configuration, connector allowlists, logging requirements, and security controls.

When used for company work, agents running on the platform are treated like any other enterprise software: they must follow the company's security, privacy, audit, and compliance policies.

The platform must integrate with:

1. Authentication, authorization, and access control systems.
2. Enterprise security monitoring.
3. Internal and third-party applications.
4. Company-approved MCP servers and related integration infrastructure.

The product should make integration and adoption as frictionless as possible. That is essential for both self-serve individual adoption and company-managed rollout.

## Core Requirements

1. **Frictionless integration**
   - Integrate with company authentication and authorization.
   - Integrate with apps and data through the browser, MCP servers, and other approved channels.

2. **Ease of use**
   - Support technical and non-technical users.
   - Let users define workflows in natural language instead of code.
   - Help users build, test, monitor, and improve workflows.

3. **Company-grade security and governance**
   - Preserve company security boundaries.
   - Provide auditability, policy enforcement, human-in-the-loop controls, rate limiting, and scope management.

## Main Features

### Integration Model

#### Browser Based Integration

The first adoption path is self-serve integration through a local web browser. The browser should ideally be integrated into the Agent Platform app, but for the 48-hour challenge PoC it is implemented as a sidecar browser via CDP.

The app runs on a laptop or desktop. The user signs in to the sites they already have access to, and agents interact with those sites through the browser. This provides:

1. Instant SSO integration.
2. Instant access to data the user can already see.
3. Minimal setup for many workflows.
4. A bottom-up, product-led adoption path where employees can try useful workflows before a centralized rollout.

The product can be thought of as an evolution of Cursor for non-technical work or an evolution of Comet + Perplexity: a natural-language environment where users can create and run useful workflows without writing software.

This browser-first path is useful in both Self-Managed and Company-Managed modes. The product experience should remain nearly identical; only management, policy, and audit behavior change.

#### Self-Managed and Company-Managed Modes

The platform should be understood as one product with two management modes, not two separate architectures.

1. **Self-Managed mode**
   - The end user manages configuration.
   - Workflows, settings, connector credentials, run transcripts, and logs stay in the local store unless the user explicitly configures otherwise.
   - The user chooses which LLM endpoints, MCP servers, and tools to use.
   - The user can still access company apps, company SaaS accounts, and company workflows when they authenticate through company SSO or the relevant company app account.
   - Company systems still enforce their own AAA, so they remain behind the company's virtual firewall even when the Agent Platform node is self-managed.
   - This mode can be free and can drive bottom-up adoption because employees can use company apps without requiring Company IT to deploy or configure the Agent Platform first.

2. **Company-Managed mode**
   - Company IT manages or constrains configuration through Agent Platform Inc.'s management portal.
   - Company IT logs into Agent Platform Inc. to define policies, approve connectors, configure allowed LLM endpoints and tools, view dashboards, and review audit logs.
   - End users must log into the Agent Platform product before using a Company-Managed Agent Platform node.
   - Audit logs, including chats and tool-call history, are stored by Agent Platform Inc. on the company's behalf and may also be exported to the company's log store or SIEM.
   - LLM endpoints, MCP servers, built-in tools, browser access, data scopes, and other integration points may be restricted by policy.
   - Security and governance policies, including future governance firewall features, can be applied centrally.

**PoC note:** The current PoC implements the Self-Managed mode.

#### Integration via MCP Servers

The MCP ecosystem can connect the platform to thousands of SaaS applications. In Self-Managed mode, users can configure their own MCP servers and credentials. In Company-Managed mode, Company IT can approve which MCP servers are available, constrain scopes, and require company-managed OAuth. Auth tokens are stored in approved infrastructure and injected into MCP calls, so upstream audit logs reflect the actual user's identity rather than a shared service account.

### Ease of Use

The core unit of work is a **workflow**: a natural-language program that the platform can run.

The product should include:

1. Natural-language workflow authoring.
2. An agent "IDE" that helps users develop, test, and debug workflows.
3. Runtime scaffolding that makes workflows more reliable, such as dynamically rendering a GUI for the workflow.
4. Prompt-building support, including a prompt compiler that rewrites rough instructions into detailed agent-ready prompts.

### Security and Governance

In Company-Managed mode, the Agent Platform inherits the company's governance model because Company IT controls policy and configuration through Agent Platform Inc.'s management portal. End users authenticate to the Agent Platform product before using a Company-Managed node. AAA is still federated across systems: company identity authenticates the user where needed, and downstream apps such as Google Workspace, Slack, Salesforce, MCP servers, or internal tools enforce their own authentication, authorization, and audit rules. This does not require the product to run behind a literal network firewall: many identity providers, SaaS apps, MCP servers, and LLM gateways are themselves third-party services. The relevant boundary is the company's identity, policy, audit, and data-governance boundary.

The platform should enforce or support:

1. Authentication and authorization.
2. Audit logs.
3. Human-in-the-loop approval.
4. Rate limits.
5. Per-workflow tool and data scopes.
6. Company IT configuration and oversight in Company-Managed mode.

Potential future governance firewall features:

1. Prompt compliance checks.
2. Prompt-injection inspection for chat context.
3. LLM output compliance checks.
4. Tool-call inspection and policy enforcement.

## Workflow Model

A workflow is the central unit of computation. The user defines a workflow, and the platform runs it.

A workflow contains:

1. **Prompts**
   - System and user prompts.
   - Natural-language instructions written by the user.
   - References to internal or external websites when needed.

2. **Tools**
   - Built-in tools such as browser access, local file reads, web fetches, and search.
   - MCP tools selected by the user or approved by the organization.

3. **Agent Runtime**
   - The execution environment that runs the workflow and the specific algorithm used by the Agent Runtime, such as Single Turn, ReAct, planner/executor, multi-agent review, or MCTS.

Workflows can run on demand or automatically. Runs should produce chat threads that are viewable, interruptible, and resumable.

In Self-Managed mode, workflows, settings, runs, transcripts, and logs stay local by default, but workflows can still operate against company apps when the user has access through company AAA. In Company-Managed mode, the same product stores audit logs, chats, dashboards, policy, and configuration with Agent Platform Inc. on the company's behalf, while constraining settings and integration points according to IT policy.

## Agent Runtime

The Agent Runtime defines how a workflow runs, including single-pass execution, tool-calling loops, multi-agent coordination, memory, and skill reuse.

The simplest Runtime Algorithm is **Single-Turn + Multiple Toolcalls**. There is only one agent. The workflow stops when the LLM returns a response that is not a tool call. During the run, the LLM may call tools such as browser navigation, web search, file reads, or MCP actions.

More advanced Runtime Algorithms may include:

1. ReAct-style reasoning and acting loops.
2. Planner/executor flows.
3. Multi-agent review workflows with orchestrators, planners, verifiers, and summarizers.
4. Monte Carlo Tree Search (MCTS) or LATS-style exploration.
5. Runtime memory and learned skills.

Runtime Algorithms are maintained by the Agent Platform team.

## Competition

This market is likely to become competitive. Products and categories to watch include Claude Cowork, Hermes, OpenClaw, Perplexity/Comet, Cursor, and other agent harness products.

Many current products still require a high level of technical skill from the user. The Agent Platform should differentiate by expanding the target user base: it must be easy to install, use, integrate, and secure. The goal is to become the "iPhone for agentic apps".

This strategy motivates several product ideas:

1. Local-browser integration.
2. Workflow builder and prompt compiler.
3. Built-in governance firewall and policy enforcement.
4. Auto-generated workflow GUIs.

## Unresolved Issues

1. **Company-managed deployment model**
   - The product should remain essentially the same across Self-Managed and Company-Managed modes. The main open question is which pieces of management should be central by default in Agent Platform Inc.'s control plane: policy distribution, audit storage/export, connector allowlists, secret storage, and optional managed runtime infrastructure.

2. **Browser integration UX**
   - The current PoC requires a separate Chrome instance started in developer mode with `make chrome-debug`.
   - This is clunky and should be improved.

3. **Browser integration stability**
   - Chrome DevTools Protocol (CDP) can change over time.
   - Cloudflare Browser Rendering MCP may help, but it does not fully replace the rich local browser integration exposed through CDP.
   - Bundling a browser, as Perplexity and Cursor do, may be a better long-term option.

4. **Browser writes and computer use**
   - Browser access is reliable enough for reading in many cases.
   - Writing or editing through a UI requires a computer-use tool, which is slower, more expensive, and less reliable.

5. **MCP brittleness**
   - Third-party MCP servers such as Zapier and Cloudflare may look like a solved integration layer, but many still depend on traditional software APIs.
   - If those underlying APIs break or change, MCP integrations can still fail.
