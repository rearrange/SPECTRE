# SPECTRE

**S**ynthetic **P**laywright **E**ngine for **C**ontinuous **T**esting, **R**eview & **E**xecution

> *A ghost that haunts your app — so your team doesn't have to.*

SPECTRE is a multi-agent AI system that converts plain-text manual test case documents into
runnable Playwright TypeScript test scripts. You write the test case in plain English. SPECTRE
reads it, browses your app, and generates the automation code.

**Status:** Active development — Phase 4 of 9 complete.

---

## How it works

SPECTRE chains a series of specialised AI agents, each responsible for one step:

```
Plain-text test case + App URL
           │
           ▼
   ┌───────────────┐
   │ Analyst Agent │  Reads the test case document
   │               │  → extracts title, steps, assertions, test data
   └───────┬───────┘
           │ structured JSON
           ▼
   ┌───────────────┐
   │ Browser Agent │  Navigates the app URL with a real headless browser
   │               │  → observes interactive elements, forms, navigation
   └───────┬───────┘
           │ UI observation JSON
           ▼
   ┌───────────────┐
   │  Coder Agent  │  Combines test plan + UI observations
   │               │  → generates a complete Playwright TypeScript .spec.ts
   └───────┬───────┘
           │ .spec.ts string
           ▼
     [ Phases 5–9 ]
     Reviewer, Git, Web UI
```

The generated script follows Playwright best practices: role-based selectors, AAA structure
(Arrange / Act / Assert), and descriptive test names.

---

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- An Anthropic API key (`ANTHROPIC_API_KEY`)

---

## Setup

**1. Clone and install dependencies**

```bash
git clone <repo-url>
cd SPECTRE
uv sync
```

**2. Install the Playwright browser**

```bash
uv run playwright install chromium
```

**3. Configure your API key**

```bash
cp .env.example .env
```

Open `.env` and fill in your key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Running the pipeline

**Flow B — new project (no existing repo):**

```bash
uv run python orchestrator.py path/to/test_case.txt https://demo.playwright.dev/todomvc
```

**Flow A — existing repo:**

```bash
uv run python orchestrator.py path/to/test_case.txt https://staging.example.com https://gitlab.example.com/your/repo
```

**What it does (in order):**

1. Analyst Agent reads the test case and extracts structured JSON
2. Browser Agent navigates the staging URL with headless Chromium and observes the UI
3. Coder Agent generates a Playwright TypeScript `.spec.ts` file from both outputs

**Output:** Full result JSON printed to stdout, followed by the generated `.spec.ts` content.

### Test case format

SPECTRE accepts any plain-text layout — the Analyst Agent uses an LLM to extract structure,
so rigid formatting is not required. A recommended layout:

```
TEST CASE: TC-001 — Feature Name

Objective:
One or two sentences describing what is being verified.

Preconditions:
- Condition one
- Condition two

Test Steps:
Step 1:
  Action: What the tester does
  Expected Result: What should happen

Assertions:
- Verifiable outcome

Test Data:
  key: value
```

---

## Running the tests

SPECTRE has a pytest test suite that verifies each agent's behaviour. Tests are split by tier:

### Full suite (all agents, all tiers)

Takes ~3–4 minutes. Makes live API calls and launches a real browser.

```bash
uv run pytest tests/ -v
```

### Fast suite — Tier 1 only (no e2e)

All tests with hardcoded fixtures. LLM calls are still made for agent unit tests.

```bash
uv run pytest tests/ -v -m "not e2e"
```

### Per-agent tests

```bash
uv run pytest tests/test_analyst_agent.py -v
uv run pytest tests/test_browser_agent.py -v
uv run pytest tests/test_coder_agent.py -v
uv run pytest tests/test_orchestrator.py -v
```

### Orchestrator — Tier 2 e2e only

Runs the full pipeline (Flow A and Flow B) with live API and Playwright against TodoMVC.

```bash
uv run pytest tests/test_orchestrator.py -v -m e2e
```

---

## Project structure

```
SPECTRE/
├── agent_base.py              # Abstract base class for all agents (ReAct loop skeleton)
├── orchestrator.py            # Orchestrator class + flow routing + CLI entry point
├── agents/
│   ├── analyst_agent.py       # Extracts structured JSON from plain-text test cases
│   ├── browser_agent.py       # Navigates a URL, returns UI observation JSON
│   ├── coder_agent.py         # Generates Playwright TypeScript .spec.ts
│   ├── reviewer_agent.py      # Stub — Phase 5
│   ├── repo_reader_agent.py   # Stub — Phase 6
│   ├── scaffold_agent.py      # Stub — Phase 6
│   └── git_agent.py           # Stub — Phase 7
├── llm/
│   ├── base.py                # LLMProvider ABC + LLMResponse dataclass
│   ├── anthropic_provider.py  # Default provider (Claude)
│   └── openai_provider.py     # Drop-in swap (not yet implemented)
├── tools/
│   └── browser_tools.py       # Async Playwright wrappers used by BrowserAgent
├── tests/                     # pytest suite — one file per agent + orchestrator
└── output/                    # Generated scripts land here (gitignored)
```

---

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | Analyst Agent — extracts test case structure as JSON |
| 2 | ✅ Complete | Browser Agent — headless Chromium UI observation |
| 3 | ✅ Complete | Coder Agent — generates Playwright TypeScript `.spec.ts` |
| 4 | ✅ Complete | Orchestrator — wires full pipeline with flow routing and retry hook |
| 5 | Planned | Reviewer Agent + retry loop |
| 6 | Planned | Repo Reader Agent + Scaffold Agent |
| 7 | Planned | Git Agent — branch, commit, push, MR/PR |
| 8 | Planned | FastAPI backend + Web UI |
| 9 | Planned | Polish + CTO demo |

---

## LLM provider

SPECTRE uses Anthropic Claude by default. Swapping to OpenAI requires changing one line:

```python
# In any agent or orchestrator file
llm = AnthropicProvider()   # → OpenAIProvider()
```

The `OpenAIProvider` stub is in place — implementation is deferred until needed.
