# SPECTRE

**S**cript **P**roduction **E**ngine for **C**omprehensive **T**est **R**unner **E**xecution

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
   [ Phase 2+ ]
   Writer Agent  →  Playwright TS script
   Reviewer Agent → quality gate
   Output
```

**Phase 1 (complete):** The Analyst Agent reads a test case document and returns a structured JSON object that all downstream agents can consume.

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

**3. Configure your API key**

```bash
cp .env.example .env
```

Open `.env` and set your key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Usage

### Run the analyst on a test case file

Write your test case as a plain-text document (see `Format` below), then:

```bash
uv run python orchestrator.py path/to/your_test_case.txt
```

The extracted structure is printed as JSON to stdout:

```json
{
  "title": "TC-001 — User Login",
  "preconditions": ["Application is accessible at https://app.example.com/login"],
  "steps": [
    {
      "step_number": 1,
      "action": "Navigate to https://app.example.com/login",
      "expected_result": "Login page is displayed"
    }
  ],
  "assertions": ["Successful login redirects to /dashboard"],
  "test_data": {
    "valid_username": "testuser@example.com",
    "valid_password": "P@ssw0rd!"
  }
}
```

### Run the test suite

```bash
uv run pytest tests/ -v
```

Tests make live calls to the Anthropic API. Expect ~30 seconds for the full suite.

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
│   └── analyst_agent.py   # Analyst: plain text → structured JSON
├── llm/
│   ├── base.py            # LLMProvider ABC and LLMResponse dataclass
│   ├── anthropic_provider.py
│   └── openai_provider.py # Stub — not yet implemented
├── tests/
│   ├── conftest.py
│   └── test_analyst_agent.py
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
uv run basedpyright llm/ agents/ agent_base.py orchestrator.py
```

Both must be clean before committing.

---

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | Complete | Analyst Agent — extracts test case structure as JSON |
| 2 | Planned | Writer Agent — generates a Playwright TypeScript test script |
| 3 | Planned | Reviewer Agent — validates the generated script |
| 4 | Planned | End-to-end pipeline with file output to `output/` |

---

## Supported LLM providers

| Provider | Status |
|----------|--------|
| Anthropic (Claude) | Supported |
| OpenAI | Stub — not yet implemented |
