# SPECTRE

**S**ynthetic **P**laywright **E**ngine for **C**ontinuous **T**esting, **R**eview & **E**xecution

> *A ghost that haunts your app — so your team doesn't have to.*

SPECTRE is a multi-agent AI system that converts plain-text manual test case documents into
runnable Playwright TypeScript test scripts. You write the test case in plain English. SPECTRE
reads it, browses your app, and generates the automation code.

**Status:** Active development — Phase 3 of 9 complete.

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
     [ Phases 4–9 ]
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

SPECTRE currently runs from the command line. Provide a plain-text test case file and a
target URL:

```bash
uv run python orchestrator.py path/to/test_case.txt https://your-staging-url.example.com
```

The pipeline runs all three agents in sequence and prints the output as JSON to stdout.
The generated TypeScript script is included in the `coder` key of the output.

### Running a single agent

You can run individual agents in isolation for debugging or exploration:

```bash
# Analyst only — extracts structure from a test case file, no browser needed
uv run python orchestrator.py --analyst-only path/to/test_case.txt

# Browser only — observes a URL, no test case needed
uv run python orchestrator.py --browser-only https://your-staging-url.example.com
```

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

Takes ~3 minutes. Makes live API calls and launches a real browser.

```bash
uv run pytest tests/ -v
```

### Per-agent tests

```bash
uv run pytest tests/test_analyst_agent.py -v
uv run pytest tests/test_browser_agent.py -v
uv run pytest tests/test_coder_agent.py -v
```

### Coder Agent — Tier 1 only (fast, no browser)

Tier 1 tests use hardcoded fixtures. No browser is launched, but LLM calls are still made.
Run these during active development to keep feedback loops short.

```bash
uv run pytest tests/test_coder_agent.py -v -m "not e2e"
```

### Coder Agent — Tier 2 e2e only

Runs the full Analyst → Browser → Coder chain with a live browser. Slow and expensive —
run once per session at most.

```bash
uv run pytest tests/test_coder_agent.py -v -m e2e
```

---

## Project structure

```
SPECTRE/
├── agent_base.py              # Abstract base class for all agents (ReAct loop skeleton)
├── orchestrator.py            # Pipeline wiring + CLI entry point
├── agents/
│   ├── analyst_agent.py       # Extracts structured JSON from plain-text test cases
│   ├── browser_agent.py       # Navigates a URL, returns UI observation JSON
│   └── coder_agent.py         # Generates Playwright TypeScript .spec.ts
├── llm/
│   ├── base.py                # LLMProvider ABC + LLMResponse dataclass
│   ├── anthropic_provider.py  # Default provider (Claude)
│   └── openai_provider.py     # Drop-in swap (not yet implemented)
├── tools/
│   └── browser_tools.py       # Async Playwright wrappers used by BrowserAgent
├── tests/                     # pytest suite — one file per agent
└── output/                    # Generated scripts land here (gitignored)
```

---

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | Analyst Agent — extracts test case structure as JSON |
| 2 | ✅ Complete | Browser Agent — observes the app with a real headless browser |
| 3 | ✅ Complete | Coder Agent — generates Playwright TypeScript .spec.ts |
| 4 | 🔜 Next | Orchestrator — wires all agents into a single pipeline with file output |
| 5 | Planned | Reviewer Agent — validates the generated script, triggers retry loop |
| 6 | Planned | Repo Reader + Scaffold — matches existing repo conventions or scaffolds a new project |
| 7 | Planned | Git Agent — branch, commit, push, open MR/PR |
| 8 | Planned | FastAPI + Web UI — tester-facing interface |
| 9 | Planned | Polish + CTO demo |

---

## LLM provider

SPECTRE uses Anthropic Claude by default. Swapping to OpenAI requires changing one line:

```python
# In any agent or orchestrator file
llm = AnthropicProvider()   # → OpenAIProvider()
```

The `OpenAIProvider` stub is in place — implementation is deferred until needed.
