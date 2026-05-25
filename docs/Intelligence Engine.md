# Product Requirements Document: Enterprise Agent Platform (a.k.a. AA Firewall)

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

The **Enterprise Agent Platform** securely hosts a company's agentic workflows. Agents running on the platform are treated like any other enterprise software: they must follow the company's security, privacy, audit, and compliance policies.

The platform must integrate with:

1. Authentication, authorization, and access control systems.
2. Enterprise security monitoring.
3. Internal and third-party applications.
4. Company-approved MCP servers and related integration infrastructure.

The product should make integration and adoption as frictionless as possible. That is essential for both enterprise rollout and bottom-up adoption.

## Core Requirements

1. **Frictionless integration**
   - Integrate with company authentication and authorization.
   - Integrate with apps and data through the browser, MCP servers, and other approved channels.

2. **Ease of use**
   - Support technical and non-technical users.
   - Let users define workflows in natural language instead of code.
   - Help users build, test, monitor, and improve workflows.

3. **Enterprise-grade security**
   - Preserve company security boundaries.
   - Provide auditability, policy enforcement, human-in-the-loop controls, rate limiting, and scope management.

## Main Features

### Enterprise Integration

#### Local Browser Integration

The first adoption path is self-serve integration through a local web browser. The browser should ideally be integrated into the Agent Platform app, but for the 48 hour challenge PoC I've integrated a sidecar browswer via CDP. 

The app runs on a laptop or desktop. The user signs in to the sites they already have access to, and agents interact with those sites through the browser. This provides:

1. Instant SSO integration.
2. Instant access to data the user can already see.
3. Minimal setup for many workflows.
4. A bottom-up, product-led adoption path where employees can try useful workflows before a centralized rollout.

The product can be thought of as an evolution of Cursor for non-technical work or an evolution of Comet + Perplexity: a natural-language environment where users can create and run useful workflows without writing software.

This browser-first path is also useful outside the enterprise, which supports a personal version of the product.

#### Enterprise and Personal Versions

The platform can support two deployment models:

1. **Enterprise version**
   - Users sign in with company SSO.
   - Workflows, settings, and runs are stored in a central IT-controlled database.
   - Runs and workflow definitions can be inspected for security and compliance.

2. **Personal version**
   - Workflows and settings are stored locally on the user's laptop.
   - The user does not need to sign in to the platform itself.
   - This version can be free and can drive bottom-up adoption.

**PoC note:** The current PoC implements the personal version.

#### MCP Server Integration

The MCP ecosystem can connect the platform to thousands of SaaS applications. The enterprise strategy is to integrate with third-party MCP servers that the company already trusts or is willing to approve. The Platform will implement standard authentication protocols like OAuth. Auth tokens are stored in IT-controlled infrastructure and injected into MCP calls, so upstream audit logs reflect the actual user's identity rather than a shared service account.

### Ease of Use

The core unit of work is a **workflow**: a natural-language program that the platform can run.

The product should include:

1. Natural-language workflow authoring.
2. An agent "IDE" that helps users develop, test, and debug workflows.
3. Runtime scaffolding that makes workflows more reliable. E.g., Dynamically rendering a GUI for the workflow.
4. Prompt-building support, including a prompt compiler that rewrites rough instructions into detailed agent-ready prompts.

### Enterprise Security

The Agent Platform inherits the company's security perimeter because users authenticate with company SSO. Secure connections between MCP clients and MCP servers are already a solved part of the ecosystem, but the platform must still provide a governance layer around agent execution.

The platform should enforce or support:

1. Authentication and authorization.
2. Audit logs.
3. Human-in-the-loop approval.
4. Rate limits.
5. Per-workflow tool and data scopes.
6. Company IT configuration and oversight.

Potential future firewall features:

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

Workflows and runs are stored in a central database in the enterprise version and locally in the personal version.

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
3. Built-in firewall and policy enforcement.
4. Auto-generated workflow GUIs.

## Unresolved Issues

1. **Enterprise headless deployment**
   - Headless deployment may be needed for enterprise environments, but it is not yet clear whether it is required for the first product version.

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
