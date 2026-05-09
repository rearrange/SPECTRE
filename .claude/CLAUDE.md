# CLAUDE.md — SPECTRE Project Context

## Project

- **Name:** SPECTRE
- **Description:** Multi-agent AI system that generates Playwright TypeScript test scripts from plain-text manual test case documents.
- **Current phase:** Phase 3 — Complete
- **Status:** All 27 tests passing. Linting (ruff) and type checking (basedpyright) fully clean.

---

## Phase 1 — AnalystAgent

Extracts structured JSON from plain-text manual test case documents.

### Deviations from spec

| Item | Detail |
|------|--------|
| `ruff` + `basedpyright` added | Not in spec. Added for formatting/lint and type checking (matches Zed). Configured under `[tool.pyright]` in `pyproject.toml`. |
| `@override` on all method overrides | Uses `typing.override` (stdlib ≥ 3.12). Added during basedpyright pass. |
| `_ = load_dotenv()` | Return value assigned to `_` to satisfy basedpyright's `reportUnusedCallResult`. |

---

## Phase 2 — BrowserAgent

Navigates a URL with Playwright, returns structured UI observation JSON via LLM.

### Deviations from spec

| Item | Detail |
|------|--------|
| `BaseAgent.run` return type widened | Changed to `dict[str, Any] \| Awaitable[dict[str, Any]]` so `BrowserAgent.run` (async) is a valid covariant override without `# type: ignore`. |
| Browser fixtures are function-scoped | pytest-asyncio 1.3.0 session-scoped async fixtures deadlock with function-scoped tests on both Windows and Linux. Each browser test launches its own Chromium instance (~9s/test overhead). |
| `asyncio_default_fixture_loop_scope` NOT set | Triggers the same deadlock. Not needed with function-scoped fixtures. |
| `raw_observations` set by agent, not LLM | Having the LLM re-emit its own HTML input is circular and wastes tokens. Agent sets this field directly from the truncated HTML string. |

### Key decisions

**`async def run()` overriding a sync abstract method** — base class return type widened to `dict[str, Any] | Awaitable[dict[str, Any]]` so basedpyright accepts the async override as a covariant return type without suppression.

**HTML truncated to 8000 chars before LLM call** — full TodoMVC HTML can be 50k+ chars. The first 8000 contain all structural content needed to generate the observations schema.

---

## Phase 3 — CoderAgent

Takes AnalystAgent + BrowserAgent output, generates a complete Playwright TypeScript `.spec.ts` file.

All unit test fixtures use TodoMVC (`https://demo.playwright.dev/todomvc`) as the app under test:
- TC-001: Add a New Todo Item
- TC-002: Complete a Todo Item

Tests are split into two tiers:
- **Tier 1** — fast unit tests (hardcoded fixtures, no API): `uv run pytest tests/test_coder_agent.py -v -m "not e2e"`
- **Tier 2** — e2e integration tests (live API + browser): `uv run pytest tests/test_coder_agent.py -v -m e2e`

### Deviations from spec

| Item | Detail |
|------|--------|
| e2e fixtures use `asyncio.run()` | Session-scoped async fixtures deadlock (same issue as Phase 2). Fixtures are synchronous and call `asyncio.run()` internally to drive `BrowserAgent`. |
| `e2e` pytest marker declared in `pyproject.toml` | Required to avoid `PytestUnknownMarkWarning`. |

### Key decisions

**Session-scoped e2e fixtures use `asyncio.run()`** — no outer event loop runs at fixture setup time, so `asyncio.run()` is safe. Each fixture executes the full Analyst → Browser → Coder chain once per session.

**Tier 1 tests make 11 independent LLM calls** — `coder_agent` fixture is function-scoped, one API call per test. If cost becomes a concern, a session-scoped `coder_output_add_todo` fixture can share the result across the 10 TC-001 tests.

**`CoderError` for empty LLM responses** — follows the `AnalystParseError` / `BrowserParseError` pattern. TypeScript output needs no JSON parsing; only non-emptiness is validated.

---

## Test Results

```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
plugins: anyio-4.13.0, asyncio-1.3.0
asyncio: mode=Mode.AUTO
collected 27 items

tests/test_analyst_agent.py::test_analyst_extracts_title PASSED          [  3%]
tests/test_analyst_agent.py::test_analyst_extracts_steps PASSED          [  7%]
tests/test_analyst_agent.py::test_analyst_steps_have_required_fields PASSED [ 11%]
tests/test_analyst_agent.py::test_analyst_extracts_preconditions PASSED  [ 14%]
tests/test_analyst_agent.py::test_analyst_extracts_assertions PASSED     [ 18%]
tests/test_analyst_agent.py::test_analyst_returns_valid_json_structure PASSED [ 22%]
tests/test_analyst_agent.py::test_analyst_handles_search_test_case PASSED [ 25%]
tests/test_browser_agent.py::test_browser_agent_returns_url PASSED       [ 29%]
tests/test_browser_agent.py::test_browser_agent_returns_page_title PASSED [ 33%]
tests/test_browser_agent.py::test_browser_agent_returns_interactive_elements PASSED [ 37%]
tests/test_browser_agent.py::test_browser_agent_interactive_elements_have_required_fields PASSED [ 40%]
tests/test_browser_agent.py::test_browser_agent_returns_navigation PASSED [ 44%]
tests/test_browser_agent.py::test_browser_agent_returns_page_structure PASSED [ 48%]
tests/test_browser_agent.py::test_browser_agent_returns_valid_json_structure PASSED [ 51%]
tests/test_coder_agent.py::test_coder_returns_script_key PASSED          [ 55%]
tests/test_coder_agent.py::test_coder_script_has_playwright_import PASSED [ 59%]
tests/test_coder_agent.py::test_coder_script_has_test_block PASSED       [ 62%]
tests/test_coder_agent.py::test_coder_script_has_describe_block PASSED   [ 66%]
tests/test_coder_agent.py::test_coder_script_has_expect PASSED           [ 70%]
tests/test_coder_agent.py::test_coder_script_references_app_url PASSED   [ 74%]
tests/test_coder_agent.py::test_coder_script_has_goto PASSED             [ 77%]
tests/test_coder_agent.py::test_coder_script_no_positional_selectors PASSED [ 81%]
tests/test_coder_agent.py::test_coder_script_has_aaa_comments PASSED     [ 85%]
tests/test_coder_agent.py::test_coder_script_covers_all_steps PASSED     [ 88%]
tests/test_coder_agent.py::test_coder_handles_complete_todo_input PASSED [ 92%]
tests/test_coder_agent.py::test_e2e_coder_add_todo_produces_script PASSED [ 96%]
tests/test_coder_agent.py::test_e2e_coder_complete_todo_produces_script PASSED [100%]

======================== 27 passed in 172.30s (0:02:52) ========================
```

---

## How to Run

### Setup

```bash
uv sync
uv run playwright install chromium
cp .env.example .env  # populate ANTHROPIC_API_KEY
```

### Tests

```bash
uv run pytest tests/ -v                                  # full suite
uv run pytest tests/test_coder_agent.py -m "not e2e"    # Tier 1 only (no API)
uv run pytest tests/test_coder_agent.py -m e2e           # Tier 2 e2e only
```

### Pipeline

```bash
# Full pipeline
uv run python orchestrator.py path/to/test_case.txt https://target-url.example.com

# Single agent
uv run python orchestrator.py --analyst-only path/to/test_case.txt
uv run python orchestrator.py --browser-only https://target-url.example.com
```

Each `--<agent>-only` flag is mutually exclusive. Future agents: add `run_<agent>()` in `orchestrator.py` and wire a new `--<agent>-only` flag.

### Linters

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright llm/ agents/ tools/ agent_base.py orchestrator.py
```
