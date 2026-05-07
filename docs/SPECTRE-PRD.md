# S.P.E.C.T.R.E
## Synthetic Playwright Engine for Continuous Testing, Review & Execution

> *A ghost that haunts your app — so your team doesn't have to.*

---

**Document Status:** Living Document
**Version:** 0.1.1
**Author:** Sallehin Sallehuddin, Head of QA — Pos Malaysia Berhad
**Created:** May 2026
**Last Updated:** May 2026
**Project Phase:** Phase 2 — Browser Agent + Playwright headless integration

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1.0 | May 2026 | Sallehin Sallehuddin | Initial PRD — Phase 0 complete |
| 0.1.1 | May 2026 | Sallehin Sallehuddin | Update Python version to 3.14.4 |

---

## Table of Contents

1. [Overview](#1-overview)
2. [Background & Motivation](#2-background--motivation)
3. [Goals & Non-Goals](#3-goals--non-goals)
4. [System Architecture](#4-system-architecture)
5. [Agent Roster](#5-agent-roster)
6. [User Flows](#6-user-flows)
7. [Functional Requirements](#7-functional-requirements)
8. [Technical Requirements](#8-technical-requirements)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Out of Scope (v1)](#10-out-of-scope-v1)
11. [Hosting & Deployment](#11-hosting--deployment)
12. [Hardware Requirements](#12-hardware-requirements)
13. [Network & Firewall Considerations](#13-network--firewall-considerations)
14. [Delivery Plan](#14-delivery-plan)
15. [Risks & Mitigations](#15-risks--mitigations)
16. [Open Questions](#16-open-questions)

---

## 1. Overview

SPECTRE is a multi-agent AI system that automates the generation of Playwright TypeScript test scripts. A tester provides a test case document and a staging URL. SPECTRE autonomously browses the application, reasons about the UI, generates a reviewed and runnable test script, and commits it directly to a Git repository — creating a Merge Request or Pull Request for the team to review.

SPECTRE is designed to augment QA Engineers, not replace them. It handles the repetitive, time-consuming work of translating test cases into automation scripts, freeing engineers to focus on test design, exploratory testing, and higher-order quality decisions.

---

## 2. Background & Motivation

### Context

Pos Malaysia Berhad's QA function is led by a small team of 8, mostly manual testers. Test automation coverage is low. The team's primary automation tool is Cypress, with active migration toward Playwright. A CTO-level challenge has been issued to explore whether agentic AI systems can replace or significantly augment QA functions — starting from manual execution and progressing toward full automation lifecycle coverage.

### Why SPECTRE

The highest-value, most realistic entry point for AI in QA is **automation script generation**. Writing Playwright scripts from test cases is:

- Repetitive and time-consuming
- Formulaic enough for an agent to handle well
- High-impact — every script generated is permanent test coverage

SPECTRE is also a strategic vehicle for:

- Accelerating the Cypress → Playwright migration
- Producing a credible AI POC for the CTO discovery initiative (Q2/Q3 2026)
- Demonstrating QA value through tooling innovation

### Connection to AI Discovery Initiative

SPECTRE is the primary deliverable of the internal AI tools discovery and POC initiative co-led with Yap Kah Loon. Architecture is finalised in Q2 2026. Full demo targeted Q4 2026. Rollout in phases post-approval.

---

## 3. Goals & Non-Goals

### Goals

- Generate runnable Playwright TypeScript test scripts from plain-language test cases
- Browse real staging URLs using a headless browser to observe actual UI state
- Integrate with existing GitLab and GitHub repositories
- Match existing codebase conventions when contributing to existing repos
- Scaffold a complete Playwright TypeScript project when no repo exists
- Provide a simple web UI accessible to non-technical QA team members
- Produce output that a QA Engineer reviews and approves — not blindly merges

### Non-Goals (v1)

- Replacing QA Engineers or eliminating QA headcount
- Running generated tests automatically in CI without human review
- Bulk migration of entire Cypress test suites
- Mobile app testing (Maestro — future phase)
- Multi-user support with authentication
- Persistent storage of past runs
- Self-healing selectors post-generation

---

## 4. System Architecture

### Overview

```
┌─────────────────────────────────────────────────────────┐
│                      WEB UI                             │
│         FastAPI backend + HTML/JS frontend              │
│  Input: test case, staging URL, optional repo URL       │
│  Output: generated script, MR/PR link, review verdict   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                          │
│  Routes to Flow A or Flow B based on repo URL presence  │
│  Manages sequential agent pipeline                      │
│  Handles retry loop between Coder and Reviewer          │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   [Flow A agents] [Shared agents] [Flow B agents]
   Repo Reader     Analyst         Scaffold
                   Browser
                   Coder
                   Reviewer
                   Git
```

### Technology Stack

| Layer | Choice | Reason |
|---|---|---|
| Agent system language | Python | Best ecosystem for agentic tooling, Playwright Python API |
| Generated test language | TypeScript | Team familiarity, Cypress migration continuity |
| Web framework | FastAPI | Sallehin's existing expertise |
| Package manager | uv | Fast, modern Python tooling |
| Browser automation | Playwright (Python) | Native headless control, browser-use compatible |
| LLM (default) | Anthropic Claude (claude-sonnet-4-20250514) | Primary provider |
| LLM (swap) | OpenAI GPT-4o | One-line change in provider config |
| Git operations | GitPython | Programmatic git control |
| GitLab API | python-gitlab | MR creation |
| GitHub API | PyGithub | PR creation |
| Secrets management | python-dotenv | .env file, never hardcoded |
| Agent tests | pytest | TDD-first, all agents tested |

---

## 5. Agent Roster

SPECTRE is composed of 7 specialised agents and 1 orchestrator. Each agent has a defined role, a specific set of tools, and a single clear output.

| Agent | Flow | Tools | Output |
|---|---|---|---|
| **Repo Reader** | A only | git clone, file read | Structured repo context JSON |
| **Scaffold** | B only | file write, directory create | Complete Playwright TS project structure |
| **Analyst** | Both | None (pure reasoning) | Structured test plan JSON |
| **Browser** | Both | browse_url, read_page_content, take_screenshot | UI observation JSON |
| **Coder** | Both | write_file | Playwright TypeScript .spec.ts file |
| **Reviewer** | Both | None (pure reasoning) | Verdict JSON: PASS or FAIL + feedback |
| **Git** | Both | git operations, GitLab/GitHub API | Branch, commit, push, MR/PR link |

### LLM Provider Abstraction

All agents share a common `LLMResponse` dataclass. Swapping providers requires changing one line:

```python
# Change this line only
llm = AnthropicLLM()   # → OpenAILLM()
```

---

## 6. User Flows

### Flow A — Existing Repository

```
Tester provides: test case + staging URL + Git repo URL
        │
        ▼
Repo Reader Agent
→ Clones repo
→ Reads: folder structure, naming conventions,
         existing test patterns, config files,
         helper utilities
→ Detects if Cypress repo → maps to Playwright TS equivalents
        │
        ▼
Analyst Agent
→ Reads test case + repo context
→ Extracts: preconditions, steps, assertions, test data
→ Output: structured JSON
        │
        ▼
Browser Agent
→ Navigates staging URL with real headless Chromium
→ Observes: interactive elements, forms, navigation,
            page structure, selectors
→ Output: UI observation JSON
        │
        ▼
Coder Agent
→ Receives analyst output + browser observations
→ Generates Playwright TypeScript .spec.ts
→ Matches existing repo conventions
→ Placed in correct folder
        │
        ▼
Reviewer Agent
→ Validates script against original test case
→ Checks: coverage, selector quality, assertion depth
→ Output: PASS or FAIL + actionable feedback
        │
    ┌───┴───┐
  PASS    FAIL (max 3 retries)
    │       └→ feedback to Coder → retry
    ▼
Git Agent
→ Creates branch: spectre/tc-{test-case-name}
→ Commits with descriptive message
→ Pushes branch
→ Opens MR (GitLab) or PR (GitHub)
        │
        ▼
Tester reviews MR/PR in GitLab / GitHub
```

### Flow B — New Project

```
Tester provides: test case + staging URL + project name
        │
        ▼
Scaffold Agent
→ Generates complete Playwright TS project:
  {project-name}/
  ├── tests/
  │   └── *.spec.ts
  ├── pages/
  │   └── *.page.ts
  ├── fixtures/
  ├── playwright.config.ts
  ├── tsconfig.json
  ├── package.json
  └── .gitignore
        │
        ▼
[Analyst → Browser → Coder → Reviewer pipeline]
(same as Flow A)
        │
        ▼
Git Agent
→ git init
→ Creates .gitignore
→ Initial commit with scaffolded structure
→ Creates remote repo via GitLab / GitHub API
→ Pushes main branch
        │
        ▼
Tester receives brand new repo, ready to use
```

---

## 7. Functional Requirements

### Core Pipeline

- System accepts a test case as input — plain text or uploaded file
- System accepts a staging URL as input
- System accepts an optional Git repository URL
- System auto-routes to Flow A or Flow B based on repo URL presence
- Pipeline runs all agents sequentially via the Orchestrator
- Max 3 Reviewer → Coder retry cycles before returning best-effort output with warning
- System returns clear, human-readable errors on: unreachable staging URL, invalid repo URL, inaccessible repo

### Analyst Agent

- Extracts from test case: preconditions, numbered steps, expected results, test data, assertions
- Outputs structured JSON consumed by downstream agents
- Handles plain text, uploaded .txt, and uploaded .md test case formats

### Browser Agent

- Navigates staging URL using real headless Chromium
- Identifies all interactive elements: inputs, buttons, links, forms, selects, textareas
- Maps page structure: navigation paths, observed flows, page title, URL
- Outputs structured JSON observation

### Coder Agent

- Generates complete, runnable Playwright TypeScript `.spec.ts` file
- Selector priority (strict): `data-testid` → role-based (`getByRole`, `getByLabel`) → label-based → **never** positional or nth-child
- Follows AAA structure: Arrange, Act, Assert
- Adds descriptive comments above each test block
- Matches existing repo conventions in Flow A
- Generated TypeScript passes `tsc --strict` with no errors

### Reviewer Agent

- Validates script against original structured test case
- Checks: test coverage completeness, selector reliability, assertion quality and depth, missing steps or edge cases
- Returns structured JSON: `{ verdict, issues, suggestions }`
- FAIL triggers Coder Agent retry with full feedback included in next prompt

### Repo Reader Agent (Flow A)

- Clones provided Git repo to a temporary local directory
- Reads and extracts: folder structure, naming conventions, existing `.spec.ts` patterns, `playwright.config.ts`, helper utilities and fixtures
- Detects Cypress repos and maps structure to Playwright TypeScript equivalents
- Outputs structured repo context JSON

### Scaffold Agent (Flow B)

- Generates a complete, opinionated Playwright TypeScript project structure
- Includes: `playwright.config.ts`, `tsconfig.json`, `package.json` with correct dependencies, `.gitignore`, `tests/` and `pages/` directories

### Git Agent

- Supports GitLab and GitHub — detects provider from repo URL
- Flow A: creates branch `spectre/tc-{test-case-name}`, commits, pushes, opens MR/PR
- Flow B: `git init`, creates remote repo via API, initial commit, pushes main branch
- Commit messages are descriptive and reference the test case name
- All credentials loaded from environment variables only — never hardcoded or logged

### Web UI

- Tester can paste or upload a test case
- Tester inputs staging URL
- Tester inputs optional Git repo URL
- Tester selects flow: existing repo (A) or new project (B)
- Real-time pipeline progress indicator showing currently active agent
- Generated script displayed with syntax highlighting
- Script downloadable as `.spec.ts` file
- MR/PR link shown upon successful completion
- Clear error messages shown on failure

---

## 8. Technical Requirements

### Project Structure

```
spectre/
├── agent_base.py              # Base agent class with ReAct loop
├── orchestrator.py            # Pipeline wiring + flow routing
├── llm/
│   ├── base.py                # LLMResponse dataclass
│   ├── anthropic_provider.py  # Default provider
│   └── openai_provider.py     # Drop-in swap
├── agents/
│   ├── analyst_agent.py
│   ├── browser_agent.py
│   ├── coder_agent.py
│   ├── reviewer_agent.py
│   ├── repo_reader_agent.py
│   ├── scaffold_agent.py
│   └── git_agent.py
├── tools/
│   ├── browser_tools.py       # Playwright functions + LLM schemas
│   ├── file_tools.py
│   └── git_tools.py
├── api/
│   └── main.py                # FastAPI app
├── ui/
│   └── index.html             # Simple frontend
├── tests/                     # pytest test suite for agents
├── output/                    # Generated scripts land here
├── .env.example               # Template for secrets
├── pyproject.toml
└── requirements.txt
```

### Environment Variables

```ini
# .env
ANTHROPIC_API_KEY=
OPENAI_API_KEY=           # optional, for provider swap
GITLAB_TOKEN=
GITHUB_TOKEN=
LLM_PROVIDER=anthropic    # anthropic | openai
```

### Dependencies

```
# Runtime
python==3.14.4

# Core
anthropic
playwright
fastapi
uvicorn
python-dotenv
gitpython
python-gitlab
PyGithub
uv

# Testing
pytest
pytest-asyncio
pytest-playwright
```

---

## 9. Non-Functional Requirements

- Pipeline completes within 3 minutes for a typical single-flow test case
- Generated TypeScript passes `tsc --strict` with no errors
- System never logs or exposes API keys or Git tokens
- System handles unreachable staging URLs gracefully — no unhandled exceptions
- System handles inaccessible or invalid Git repos gracefully
- Max retry cycles (3) enforced — system never loops indefinitely
- All agents individually testable in isolation via pytest

---

## 10. Out of Scope (v1)

The following are explicitly deferred to future versions:

| Feature | Reason Deferred |
|---|---|
| Running generated tests in CI automatically | Requires human review gate first |
| Bulk Cypress suite migration | High complexity, separate initiative |
| Mobile app testing (Maestro) | Different toolchain, future phase |
| Multi-user support | POC is single-user |
| Authentication on web UI | Not needed for internal POC |
| Database persistence of past runs | Adds infra complexity |
| Self-healing selectors | Post-generation concern |
| Multi-page / multi-flow test cases in one run | POC handles single flow only |
| Test reporting dashboard | Future product feature |

---

## 11. Hosting & Deployment

### Deployment Stages

| Stage | Approach | Cost |
|---|---|---|
| **Phase 1–8 (build)** | Local machine — WSL2 on Windows 11 | Free |
| **Phase 9 (CTO demo)** | Local machine — same, nothing else open | Free |
| **Internal pilot** | Hybrid: SPECTRE brain on Vultr, Browser Worker inside Pos Malaysia network | ~$24/mo |
| **Production rollout** | Full internal hosting inside Pos Malaysia, one outbound firewall rule to api.anthropic.com | TBD by IT |

### Demo Server (if needed post-POC)

- Host: Vultr (Malaysia-proximate region)
- Reverse proxy: Caddy
- Server name convention: `spectre.nyxnode.com`
- Minimum VPS spec: 4 vCPU, 8GB RAM

### Containerisation (post-POC)

```yaml
# docker-compose.yml (future)
services:
  spectre-api:        # FastAPI container
  spectre-worker:     # Agent pipeline container
  spectre-browser:    # Playwright container (mcr.microsoft.com/playwright)
```

---

## 12. Hardware Requirements

### Local Development & Demo (Windows 11 + WSL2)

| Component | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores, 2.0GHz+ | 6–8 cores, 2.5GHz+ |
| RAM | 8GB | 16GB |
| Storage | 10GB free (SSD) | 20GB free (SSD) |
| OS | Windows 10/11 64-bit | Windows 11 64-bit |

### WSL2 Configuration (`.wslconfig`)

```ini
[wsl2]
memory=6GB
processors=4
swap=2GB
```

### RAM Breakdown During a Pipeline Run

| Component | RAM Usage |
|---|---|
| Headless Chromium | ~300–500MB |
| Python agents | ~200–300MB |
| FastAPI server | ~100MB |
| Corporate apps (Teams, browser) | ~2–4GB |
| **Total SPECTRE need** | **~600–900MB** |

---

## 13. Network & Firewall Considerations

### The Core Problem

SPECTRE requires simultaneous access to two environments:

- **Anthropic API** — external internet (`api.anthropic.com:443`)
- **Staging URLs** — internal Pos Malaysia network

These are on opposite sides of the corporate firewall.

### Options by Stage

**POC / Demo (recommended):** Run SPECTRE entirely on work laptop inside Pos Malaysia network. Outbound HTTPS to `api.anthropic.com` is typically allowed by default. Staging URLs are reachable on the same network. Zero IT involvement required.

**Internal Pilot:** Hybrid architecture — SPECTRE brain on Vultr (reaches Anthropic API), Browser Worker as a lightweight process running inside Pos Malaysia network (reaches staging URLs, polls Vultr for tasks via outbound HTTPS). Minimal IT ask — no inbound firewall changes needed.

**Production:** SPECTRE fully hosted on internal Pos Malaysia server. IT opens one outbound whitelist rule: `api.anthropic.com:443`. Clean, scalable, no external dependency for the browser component.

### Pre-Demo Checklist

- [ ] Outbound HTTPS to `api.anthropic.com` not blocked from work laptop
- [ ] Staging URL reachable from work laptop
- [ ] WSL2 can reach both endpoints
- [ ] All API keys and tokens in `.env` file, not committed to repo

---

## 14. Delivery Plan

### Timeline

| Phase | Deliverable | Target |
|---|---|---|
| **Phase 0** | Planning, architecture, PRD | ✅ May 2026 |
| **Phase 1** | Project setup + Analyst Agent (with pytest) | Week 1–2 |
| **Phase 2** | Browser Agent + Playwright headless integration | Week 3–4 |
| **Phase 3** | Coder Agent + TypeScript file output | Week 5–6 |
| **Phase 4** | Orchestrator — wire Analyst + Browser + Coder | Week 7–8 |
| **Phase 5** | Reviewer Agent + retry loop | Week 9–10 |
| **Phase 6** | Repo Reader Agent + Scaffold Agent | Week 11–12 |
| **Phase 7** | Git Agent — branch, commit, push, MR/PR | Week 13–14 |
| **Phase 8** | FastAPI backend + Web UI | Week 15–16 |
| **Phase 9** | Polish, error handling, CTO demo prep | Week 17–18 |

### Q2 2026 Report Narrative

> SPECTRE (Synthetic Playwright Engine for Continuous Testing, Review & Execution) is in active development. System architecture has been finalised and Phase 0 planning is complete. Development begins Q3 2026. Full CTO demo targeted Q4 2026, with internal rollout planning to follow pending approval.

---

## 15. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Anthropic API blocked by Pos Malaysia firewall | Medium | High | Run demo on personal hotspot if needed; long-term use internal hosting |
| Headless Chromium too heavy for demo laptop | Low | High | 16GB RAM recommended; close all other apps during demo |
| Generated selectors brittle on complex UIs | Medium | Medium | Reviewer Agent enforces selector quality; human reviews MR/PR |
| LLM hallucinates test steps not in test case | Low | Medium | Analyst Agent structures input strictly; Reviewer Agent catches deviations |
| GitLab/GitHub API token permission issues | Low | Medium | Document required token scopes clearly in setup guide |
| Solo development bandwidth | High | Medium | Phase-by-phase delivery — something working at every stage |

---

## 16. Open Questions

| # | Question | Status |
|---|---|---|
| 1 | Will Pos Malaysia IT provision an internal server for production hosting? | Open |
| 2 | Which GitLab group/namespace should SPECTRE-generated repos live under? | Open |
| 3 | Should generated scripts follow an existing Pos Malaysia Playwright convention or establish a new one? | Open |
| 4 | Will budget be approved for Anthropic API usage post-POC? | Open |
| 5 | Should SPECTRE support Jira ticket URLs as test case input (in addition to plain text)? | Open |
| 6 | Multi-agent framework evaluation — LangGraph vs CrewAI vs custom (current approach)? | Open |

---

*This is a living document. Update the revision history table with every significant change.*
