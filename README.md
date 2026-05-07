# SPECTRE

**S**ynthetic **P**laywright **E**ngine for **C**ontinuous **T**esting, **R**eview & **E**xecution

A multi-agent AI system that converts plain-text manual test case documents into runnable Playwright TypeScript test scripts.

---

## How it works

SPECTRE chains a series of specialised AI agents, each responsible for one step of the transformation pipeline:

```
Plain-text test case
        │
        ▼
┌───────────────┐
│ Analyst Agent │  Extracts structure from the raw document
│               │  → title, steps, assertions, test data
└───────┬───────┘
        │  (structured JSON)
        ▼
┌───────────────┐
│ Browser Agent │  Navigates the target URL with Playwright
│               │  → interactive elements, navigation, page structure
└───────┬───────┘
        │  (page observations JSON)
        ▼
   [ Phase 3+ ]
   Writer Agent  →  Playwright TS script
   Reviewer Agent → quality gate
   Output
```

**Phase 1 (complete):** The Analyst Agent reads a test case document and returns a structured JSON object.

**Phase 2 (complete):** The Browser Agent navigates the target URL headlessly, observes the page with Playwright, and returns a structured description of the UI (interactive elements, navigation, page structure).

---

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (package manager)
- An Anthropic API key

---

## Setup

**1. Clone the repository**

```bash
git clone <repo-url>
cd SPECTRE
```

**2. Install dependencies**

```bash
uv sync
```

**3. Install the Chromium browser binary**

```bash
uv run playwright install chromium
```

**4. Configure your API key**

```bash
cp .env.example .env
```

Open `.env` and set your key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Usage

### Run the full pipeline (Analyst → Browser)

Provide a plain-text test case file and the URL of the page to analyse:

```bash
uv run python orchestrator.py path/to/your_test_case.txt https://your-staging-url.example.com
```

Output is JSON printed to stdout with two top-level keys:

```json
{
  "analyst": {
    "title": "TC-001 — User Login",
    "preconditions": ["..."],
    "steps": [{ "step_number": 1, "action": "...", "expected_result": "..." }],
    "assertions": ["..."],
    "test_data": {}
  },
  "browser": {
    "url": "https://your-staging-url.example.com",
    "page_title": "My App",
    "interactive_elements": [
      { "type": "input", "label": "Email", "selector": "#email", "placeholder": "Enter email" }
    ],
    "forms": [],
    "navigation": { "links": ["/about", "/login"], "current_path": "/" },
    "page_structure": "A login page with email and password fields...",
    "raw_observations": "..."
  }
}
```

### Run the Analyst Agent alone

To extract structure from a test case without browser navigation:

```bash
uv run python -c "
from agents.analyst_agent import AnalystAgent
from llm.anthropic_provider import AnthropicProvider
import json, sys

agent = AnalystAgent(AnthropicProvider())
result = agent.run({'test_case': open(sys.argv[1]).read()})
print(json.dumps(result, indent=2))
" path/to/your_test_case.txt
```

### Run the Browser Agent alone

To inspect a URL without a test case:

```bash
uv run python -c "
import asyncio, json
from playwright.async_api import async_playwright
from agents.browser_agent import BrowserAgent
from llm.anthropic_provider import AnthropicProvider

async def main():
    agent = BrowserAgent(AnthropicProvider())
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        result = await agent.run({'url': 'https://demo.playwright.dev/todomvc', 'page': page})
        await browser.close()
    print(json.dumps(result, indent=2))

asyncio.run(main())
"
```

### Run the test suite

```bash
uv run pytest tests/ -v
```

Tests make live calls to the Anthropic API and navigate real URLs with Playwright. Expect ~90 seconds for the full suite (14 tests).

---

## Test case format

SPECTRE accepts any plain-text layout. The Analyst Agent uses an LLM to extract structure, so rigid formatting is not required. A recommended layout:

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

## Project structure

```
SPECTRE/
├── agent_base.py          # Abstract BaseAgent with ReAct loop skeleton
├── orchestrator.py        # Chains agents into a pipeline; CLI entry point
├── agents/
│   ├── analyst_agent.py   # Analyst: plain text → structured JSON
│   └── browser_agent.py   # Browser: URL → page observations JSON
├── llm/
│   ├── base.py            # LLMProvider ABC and LLMResponse dataclass
│   ├── anthropic_provider.py
│   └── openai_provider.py # Stub — not yet implemented
├── tools/
│   └── browser_tools.py   # Async Playwright wrappers (browse_url, get_interactive_elements, …)
├── tests/
│   ├── conftest.py
│   ├── test_analyst_agent.py
│   └── test_browser_agent.py
├── output/                # Generated scripts written here (gitignored)
├── .claude/
│   └── CLAUDE.md          # Project context for Claude Code sessions
├── .env.example
└── pyproject.toml
```

---

## Development

### Linting and formatting

```bash
uv run ruff check .          # lint
uv run ruff format .         # format
```

### Type checking

```bash
uv run basedpyright llm/ agents/ tools/ agent_base.py orchestrator.py
```

Both must be clean before committing.

### Debug screenshots

Set `DEBUG_SCREENSHOTS=true` in `.env` to save a screenshot of each navigated page to `output/screenshots/`.

---

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | Analyst Agent — extracts test case structure as JSON |
| 2 | ✅ Complete | Browser Agent — navigates target URL, returns page observations |
| 3 | Planned | Writer Agent — generates a Playwright TypeScript test script |
| 4 | Planned | Reviewer Agent — validates the generated script |
| 5 | Planned | End-to-end pipeline with file output to `output/` |

---

## Supported LLM providers

| Provider | Status |
|----------|--------|
| Anthropic (Claude) | Supported |
| OpenAI | Stub — not yet implemented |
