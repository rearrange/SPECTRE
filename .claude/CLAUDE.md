# CLAUDE.md — SPECTRE Project Context

## Project

- **Name:** SPECTRE
- **Description:** Multi-agent AI system that generates Playwright TypeScript test scripts from plain-text manual test case documents.
- **Current phase:** Phase 4 — Complete
- **Status:** All 38 tests passing. Linting (ruff) and type checking (basedpyright) fully clean.

## Current File Tree

```
SPECTRE/
├── .env.example
├── .gitattributes
├── .gitignore
├── agent_base.py              # Abstract BaseAgent with ReAct loop skeleton
├── orchestrator.py            # Orchestrator class + flow routing + CLI entry point
├── pyproject.toml
├── uv.lock
├── agents/
│   ├── __init__.py            # Exports all agents + their errors
│   ├── analyst_agent.py       # Extracts structured JSON from plain-text test cases
│   ├── browser_agent.py       # Navigates URL with Playwright, returns UI observation JSON
│   ├── coder_agent.py         # Takes Analyst + Browser JSON, generates Playwright TS .spec.ts
│   ├── reviewer_agent.py      # Stub — always returns PASS; to be implemented in Phase 5
│   ├── repo_reader_agent.py   # Stub — returns placeholder dict; to be implemented in Phase 6
│   ├── scaffold_agent.py      # Stub — returns placeholder dict; to be implemented in Phase 6
│   └── git_agent.py           # Stub — returns placeholder dict; to be implemented in Phase 7
├── llm/
│   ├── __init__.py
│   ├── base.py                # LLMProvider ABC + LLMResponse dataclass
│   ├── anthropic_provider.py  # Live Anthropic (Claude) provider
│   └── openai_provider.py     # OpenAI stub (NotImplementedError)
├── tools/
│   ├── __init__.py
│   └── browser_tools.py       # Async Playwright wrappers: browse_url, get_page_content, etc.
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Shared fixtures: TodoMVC test cases, hardcoded JSON, agents
│   ├── test_analyst_agent.py  # 7 tests — AnalystAgent contract
│   ├── test_browser_agent.py  # 7 tests — BrowserAgent contract
│   ├── test_coder_agent.py    # 13 tests — CoderAgent contract (11 Tier 1 + 2 Tier 2 e2e)
│   └── test_orchestrator.py   # 11 tests — Orchestrator contract (9 Tier 1 + 2 Tier 2 e2e)
└── output/
    └── .gitkeep               # Tracks gitignored output directory
```

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

## Phase 4 — Orchestrator

Wires the full pipeline with flow routing (Flow A / Flow B) and a structurally-present reviewer retry hook. Stub agents are in place for Reviewer, RepoReader, Scaffold, and Git — all return placeholder values and are designed to be swapped in later phases with zero orchestrator changes.

- **Flow A** (`repo_url` present): RepoReader stub → Analyst → Browser → Coder → Reviewer stub → Git stub
- **Flow B** (`repo_url` absent): Scaffold stub → Analyst → Browser → Coder → Reviewer stub → Git stub
- **`MAX_RETRIES = 3`** — retry loop is structurally wired; stub always returns PASS so retries is always 0 in normal operation

Tests are split into two tiers:
- **Tier 1** — 9 unit tests (all agents mocked via `MagicMock`, no network, no browser): `uv run pytest tests/test_orchestrator.py -v -m "not e2e"`
- **Tier 2** — 2 e2e integration tests (live API + Playwright, TodoMVC): `uv run pytest tests/test_orchestrator.py -v -m e2e`

### Deviations from spec

| Item | Detail |
|------|--------|
| Unit tests mock `_run_browser` not `_browser.run` | Mocking the sync wrapper avoids launching Chromium in Tier 1 tests. Mocking the async `_browser.run` would still require `asyncio.run()` + Playwright context setup, defeating the purpose. |
| E2e tests call `orch.run()` directly (no `asyncio.run()`) | `Orchestrator.run()` is synchronous and uses `asyncio.run()` internally for the browser step. The test body needs no async handling. |

### Key decisions

**`Orchestrator._run_browser()` is synchronous** — wraps the async Playwright flow in `asyncio.run()`, making `Orchestrator.run()` fully synchronous and easy to call from tests and the CLI without async ceremony.

**Agents created internally in `__init__`** — all agents share the same `LLMProvider` instance passed to the Orchestrator. No agent wiring needed at the call site.

**Retry loop uses `for/else`** — the `else` branch sets `retries = MAX_RETRIES - 1` when the loop exhausts without a PASS, matching the spec's contract exactly.

---

## Test Results

```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0 -- /home/rearrange/Codes/GitLab/spectre/.venv/bin/python
cachedir: .pytest_cache
rootdir: /home/rearrange/Codes/GitLab/spectre
configfile: pyproject.toml
plugins: anyio-4.13.0, asyncio-1.3.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 38 items

tests/test_analyst_agent.py::test_analyst_extracts_title PASSED          [  2%]
tests/test_analyst_agent.py::test_analyst_extracts_steps PASSED          [  5%]
tests/test_analyst_agent.py::test_analyst_steps_have_required_fields PASSED [  7%]
tests/test_analyst_agent.py::test_analyst_extracts_preconditions PASSED  [ 10%]
tests/test_analyst_agent.py::test_analyst_extracts_assertions PASSED     [ 13%]
tests/test_analyst_agent.py::test_analyst_returns_valid_json_structure PASSED [ 15%]
tests/test_analyst_agent.py::test_analyst_handles_search_test_case PASSED [ 18%]
tests/test_browser_agent.py::test_browser_agent_returns_url PASSED       [ 21%]
tests/test_browser_agent.py::test_browser_agent_returns_page_title PASSED [ 23%]
tests/test_browser_agent.py::test_browser_agent_returns_interactive_elements PASSED [ 26%]
tests/test_browser_agent.py::test_browser_agent_interactive_elements_have_required_fields PASSED [ 28%]
tests/test_browser_agent.py::test_browser_agent_returns_navigation PASSED [ 31%]
tests/test_browser_agent.py::test_browser_agent_returns_page_structure PASSED [ 34%]
tests/test_browser_agent.py::test_browser_agent_returns_valid_json_structure PASSED [ 36%]
tests/test_coder_agent.py::test_coder_returns_script_key PASSED          [ 39%]
tests/test_coder_agent.py::test_coder_script_has_playwright_import PASSED [ 42%]
tests/test_coder_agent.py::test_coder_script_has_test_block PASSED       [ 44%]
tests/test_coder_agent.py::test_coder_script_has_describe_block PASSED   [ 47%]
tests/test_coder_agent.py::test_coder_script_has_expect PASSED           [ 50%]
tests/test_coder_agent.py::test_coder_script_references_app_url PASSED   [ 52%]
tests/test_coder_agent.py::test_coder_script_has_goto PASSED             [ 55%]
tests/test_coder_agent.py::test_coder_script_no_positional_selectors PASSED [ 57%]
tests/test_coder_agent.py::test_coder_script_has_aaa_comments PASSED     [ 60%]
tests/test_coder_agent.py::test_coder_script_covers_all_steps PASSED     [ 63%]
tests/test_coder_agent.py::test_coder_handles_complete_todo_input PASSED [ 65%]
tests/test_coder_agent.py::test_e2e_coder_add_todo_produces_script PASSED [ 68%]
tests/test_coder_agent.py::test_e2e_coder_complete_todo_produces_script PASSED [ 71%]
tests/test_orchestrator.py::test_orchestrator_routes_flow_a_when_repo_url_present PASSED [ 73%]
tests/test_orchestrator.py::test_orchestrator_routes_flow_b_when_repo_url_absent PASSED [ 76%]
tests/test_orchestrator.py::test_orchestrator_output_has_required_keys PASSED [ 78%]
tests/test_orchestrator.py::test_orchestrator_retry_hook_increments_on_fail PASSED [ 81%]
tests/test_orchestrator.py::test_orchestrator_retry_hook_respects_max_retries PASSED [ 84%]
tests/test_orchestrator.py::test_reviewer_stub_returns_pass_verdict PASSED [ 86%]
tests/test_orchestrator.py::test_repo_reader_stub_returns_dict PASSED    [ 89%]
tests/test_orchestrator.py::test_scaffold_stub_returns_dict PASSED       [ 92%]
tests/test_orchestrator.py::test_git_stub_returns_dict PASSED            [ 94%]
tests/test_orchestrator.py::test_orchestrator_full_flow_b_todomvc PASSED [ 97%]
tests/test_orchestrator.py::test_orchestrator_full_flow_a_todomvc PASSED [100%]

======================== 38 passed in 211.44s (0:03:31) ========================
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
uv run pytest tests/ -v                                       # full suite
uv run pytest tests/ -v -m "not e2e"                         # Tier 1 only (fast)
uv run pytest tests/test_orchestrator.py -v -m "not e2e"     # Orchestrator Tier 1 only
uv run pytest tests/test_orchestrator.py -v -m e2e            # Orchestrator Tier 2 e2e only
```

### Pipeline

```bash
# Full pipeline — Flow B (new project, no repo)
uv run python orchestrator.py path/to/test_case.txt https://staging.example.com

# Full pipeline — Flow A (existing repo)
uv run python orchestrator.py path/to/test_case.txt https://staging.example.com https://gitlab.example.com/your/repo
```

Prints the full result JSON to stdout, followed by the generated `.spec.ts` content.

### Linters

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright llm/ agents/ agent_base.py orchestrator.py
```

---

## Next Phase

**Phase 5 — Reviewer Agent + retry loop**

Replace `ReviewerAgent` stub with a real LLM-based reviewer that inspects the generated Playwright TypeScript script and returns structured feedback. Wire the retry loop in `Orchestrator` to call `CoderAgent` again with the reviewer's feedback when verdict is `FAIL`.
