# CLAUDE.md — SPECTRE Project Context

## Project

- **Name:** SPECTRE
- **Description:** Multi-agent AI system that generates Playwright TypeScript test scripts from plain-text manual test case documents.
- **Current phase:** Phase 3 — Complete
- **Status:** All 27 tests passing. Linting (ruff) and type checking (basedpyright) fully clean.

---

## What Was Built in Phase 1

### File tree (Phase 1)

```
SPECTRE/
├── .env.example
├── .gitignore
├── agent_base.py          # Abstract BaseAgent with ReAct loop skeleton
├── agents/
│   ├── __init__.py
│   └── analyst_agent.py   # AnalystAgent: extracts structured JSON from test case text
├── llm/
│   ├── __init__.py
│   ├── anthropic_provider.py   # Live Anthropic (Claude) provider
│   ├── base.py                 # LLMProvider ABC + LLMResponse dataclass
│   └── openai_provider.py      # OpenAI stub (NotImplementedError)
├── orchestrator.py        # Phase 1 pipeline: instantiates and chains AnalystAgent
├── output/
│   └── .gitkeep           # Tracks gitignored output directory
├── pyproject.toml
├── tests/
│   ├── __init__.py
│   ├── conftest.py        # Fixtures: two sample test cases + analyst_agent
│   └── test_analyst_agent.py   # 7 contract tests (written before implementation)
└── uv.lock
```

### Deviations from original Phase 1 spec

| Item | Detail |
|------|--------|
| `ruff` added | Not in the Phase 1 spec. Added in a follow-up to enforce formatting and lint (E, F, I, UP, B, SIM rule sets). |
| `basedpyright` added | Not in the Phase 1 spec. Added in a follow-up to match the type checking Zed uses. Configured under `[tool.pyright]` in `pyproject.toml`. |
| `agents/__init__.py`, `llm/__init__.py`, `tests/__init__.py` | Not explicitly listed in the spec. Added as standard Python package markers required by setuptools discovery. |
| `output/.gitkeep` | Not in the spec. Added so the `output/` directory is tracked in git despite being gitignored for content. |
| `@override` on all method overrides | Added during basedpyright fix pass. Uses `typing.override` (stdlib in Python 3.12+, no extra dependency). |
| `_ = load_dotenv()` | `load_dotenv()` return value assigned to `_` to satisfy basedpyright's `reportUnusedCallResult`. |

---

## What Was Built in Phase 2

### File tree (Phase 2 additions)

```
SPECTRE/
├── agents/
│   ├── __init__.py        # Updated: exports BrowserAgent + BrowserParseError
│   └── browser_agent.py   # BrowserAgent: navigates a URL, returns structured JSON via LLM
├── tools/
│   ├── __init__.py        # Empty package marker
│   └── browser_tools.py   # Async Playwright wrappers: browse_url, get_page_title,
│                          #   get_interactive_elements, take_screenshot
├── agent_base.py          # Updated: run() return type widened to dict | Awaitable[dict]
├── orchestrator.py        # Updated: async pipeline + run_analyst/run_browser helpers + argparse CLI
└── tests/
    ├── conftest.py        # Updated: added browser/page/browser_agent async fixtures
    └── test_browser_agent.py   # 7 contract tests for BrowserAgent
```

### Deviations from Phase 2 spec

| Item | Detail |
|------|--------|
| `BaseAgent.run` return type widened | The spec's abstract `run()` returns `dict[str, Any]`. Changed to `dict[str, Any] \| Awaitable[dict[str, Any]]` so that `BrowserAgent.run` (async) is a valid covariant override accepted by basedpyright without suppression. |
| Browser/page/browser_agent fixtures are function-scoped | The spec asked for `scope="session"` on the browser fixture. In pytest-asyncio 1.3.0, session-scoped async fixtures combined with function-scoped tests cause an event loop deadlock on Windows: the session fixture body never executes. Changed all three fixtures to function scope (default). Each of the 7 browser tests launches its own Chromium instance. Runtime impact: ~9 seconds/test vs. ~2 seconds/test with a shared browser. |
| `asyncio_default_fixture_loop_scope` NOT set | The spec implied adding this config option. It was removed because it triggers the same session/function event loop deadlock on Windows with pytest-asyncio 1.3.0. The option is not needed with function-scoped fixtures. |
| `raw_observations` set by agent, not by LLM | The spec listed `raw_observations` as an LLM output field. In practice, having the LLM reproduce the full HTML it received is circular and unreliable. The agent sets `result["raw_observations"]` directly after the LLM call to `f"URL: {url}\nTitle: {page_title}\nHTML:\n{html_content[:8000]}"`. The LLM system prompt does not ask the LLM to produce this field. |
| `tools` added to `known-first-party` in ruff isort | Not in spec. Required to keep import blocks sorted correctly. |
| `tools` added to basedpyright `include` and setuptools package discovery | Not in spec. Required for type checking and package import resolution. |

### Python version and package manager

- **Python:** 3.14.4
- **Package manager:** uv 0.11.10 (x86_64-pc-windows-msvc)

---

## Test Results

### Phase 2 final pytest run (verbatim terminal output)

```
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0 -- D:\Codes\GitLab\SPECTRE\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Codes\GitLab\SPECTRE
configfile: pyproject.toml
plugins: anyio-4.13.0, asyncio-1.3.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 14 items

tests/test_analyst_agent.py::test_analyst_extracts_title PASSED          [  7%]
tests/test_analyst_agent.py::test_analyst_extracts_steps PASSED          [ 14%]
tests/test_analyst_agent.py::test_analyst_steps_have_required_fields PASSED [ 21%]
tests/test_analyst_agent.py::test_analyst_extracts_preconditions PASSED  [ 28%]
tests/test_analyst_agent.py::test_analyst_extracts_assertions PASSED     [ 35%]
tests/test_analyst_agent.py::test_analyst_returns_valid_json_structure PASSED [ 42%]
tests/test_analyst_agent.py::test_analyst_handles_search_test_case PASSED [ 50%]
tests/test_browser_agent.py::test_browser_agent_returns_url PASSED       [ 57%]
tests/test_browser_agent.py::test_browser_agent_returns_page_title PASSED [ 64%]
tests/test_browser_agent.py::test_browser_agent_returns_interactive_elements PASSED [ 71%]
tests/test_browser_agent.py::test_browser_agent_interactive_elements_have_required_fields PASSED [ 78%]
tests/test_browser_agent.py::test_browser_agent_returns_navigation PASSED [ 85%]
tests/test_browser_agent.py::test_browser_agent_returns_page_structure PASSED [ 92%]
tests/test_browser_agent.py::test_browser_agent_returns_valid_json_structure PASSED [100%]

======================== 14 passed in 88.87s (0:01:28) ========================
```

- **Total:** 14
- **Passed:** 14
- **Failed:** 0

Tests make live API calls to the Anthropic API and live browser navigations to demo.playwright.dev. Runtime is ~89 seconds due to network latency and 7 independent Chromium launches.

---

---

## What Was Built in Phase 3

### File tree (Phase 3 additions)

```
SPECTRE/
├── agents/
│   ├── __init__.py        # Updated: exports CoderAgent + CoderError
│   └── coder_agent.py     # CoderAgent: takes Analyst + Browser JSON, generates Playwright TS spec
└── tests/
    ├── conftest.py        # Updated: all fixtures replaced with TodoMVC-based scenarios + hardcoded JSON fixtures
    ├── test_analyst_agent.py  # Updated: fixture names changed to *_add_todo / *_complete_todo
    └── test_coder_agent.py    # 13 contract tests (11 Tier 1 unit + 2 Tier 2 e2e)
```

### Deviations from Phase 3 spec

| Item | Detail |
|------|--------|
| All unit test fixtures replaced with TodoMVC scenarios | `sample_test_case_login` and `sample_test_case_search` removed. Replaced with `sample_test_case_add_todo` (TC-001) and `sample_test_case_complete_todo` (TC-002). The application under test for all SPECTRE unit tests is `https://demo.playwright.dev/todomvc`. This decision was made in Phase 3 to ensure test fixtures reflect a real QA tester using SPECTRE against a real application. |
| `e2e` pytest marker added | `pyproject.toml` `[tool.pytest.ini_options]` now declares the `e2e` marker to avoid `PytestUnknownMarkWarning`. |
| Session-scoped e2e fixtures use `asyncio.run()` | The spec implied session-scoped async fixtures. On Linux with pytest-asyncio 1.3.0 function-scoped event loops, session-scoped async fixtures deadlock identically to the Windows issue documented in Phase 2. The e2e fixtures are synchronous and use `asyncio.run()` internally to drive the browser agent. |
| Local imports inside e2e fixtures | Imports for `AnalystAgent`, `BrowserAgent`, `CoderAgent`, `AnthropicProvider`, and `async_playwright` are deferred inside the fixture functions to avoid import-time side effects. Ruff isort requires stdlib (`asyncio`) separated from third-party (`playwright`) and first-party (`agents`, `llm`) blocks by a blank line — applied. |

### Python version and package manager

- **Python:** 3.14.4
- **Package manager:** uv (Linux)

---

## Test Results

### Phase 3 final pytest run (verbatim terminal output)

```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0 -- /home/rearrange/Codes/GitLab/spectre/.venv/bin/python
cachedir: .pytest_cache
rootdir: /home/rearrange/Codes/GitLab/spectre
configfile: pyproject.toml
plugins: anyio-4.13.0, asyncio-1.3.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 27 items

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

- **Total:** 27
- **Passed:** 27
- **Failed:** 0

Tier 1 unit tests (11) use hardcoded fixtures — no API calls, no browser. Runtime ~63s due to 11 LLM calls sharing the same session fixtures.
Tier 2 e2e tests (2) use the full Analyst → Browser → Coder chain with live API and Playwright. Runtime ~37s (both TC-001 and TC-002 chains).

---

## Key Implementation Decisions (Phase 3)

### Session-scoped e2e fixtures use `asyncio.run()` instead of async fixtures

The spec suggested session-scoped async fixtures. The Phase 2 deviation notes document that session-scoped async fixtures deadlock with pytest-asyncio 1.3.0 on both Windows and Linux when combined with function-scoped test event loops. To avoid the deadlock, the e2e fixtures (`e2e_coder_output_add_todo`, `e2e_coder_output_complete_todo`) are declared as synchronous functions that call `asyncio.run()` internally to drive the `BrowserAgent.run()` coroutine. This is safe because these fixtures are only called once per session and there is no outer event loop running at fixture setup time.

### Tier 1 tests run 11 independent LLM calls

Each of the 11 Tier 1 tests calls `coder_agent.run()` independently (the `coder_agent` fixture is function-scoped). This means 11 separate Anthropic API calls are made — one per test. This was intentional: each test must be independently verifiable. The runtime (~63 seconds) is acceptable for a development-phase unit test suite. If cost becomes a concern, a session-scoped `coder_output_add_todo` fixture could be introduced to share the result across the 10 TC-001 tests, reducing API calls to 2 total.

### `CoderError` for empty LLM responses

Following the `AnalystParseError` / `BrowserParseError` pattern, `CoderError` is raised when the LLM returns an empty string. JSON parsing is not needed here — the output is TypeScript source, not JSON. The only validation is non-emptiness.

---

## Key Implementation Decisions (Phase 2)

### `async def run()` on BrowserAgent overriding a sync abstract method

`BaseAgent.run` is declared as a sync abstract method. `BrowserAgent.run` is `async def` because it awaits Playwright calls. Rather than using `# type: ignore`, the base class return type was widened to `dict[str, Any] | Awaitable[dict[str, Any]]`. Covariant override checking in basedpyright then accepts `Coroutine[Any, Any, dict[str, Any]]` (which is `Awaitable[dict[str, Any]]`) as a valid override return type.

### Function-scoped browser fixtures instead of session-scoped

On Windows with pytest-asyncio 1.3.0, session-scoped async fixtures deadlock when combined with function-scoped tests (`asyncio_default_test_loop_scope=function`, the default). The browser fixture's async body is never entered — the event loop setup for the session fixture hangs indefinitely. All three browser-related fixtures (`browser`, `page`, `browser_agent`) were changed to function scope (default). Each browser agent test creates and destroys its own Chromium instance, adding ~7 seconds overhead.

### HTML truncated to 8000 chars before LLM call

The full TodoMVC HTML can be 50k+ characters. Passing the full HTML to the LLM would exceed practical token budgets and significantly increase latency/cost. The first 8000 chars contain the structural content needed to generate the observations schema.

### `raw_observations` written by the agent, not the LLM

Having the LLM re-emit its own input as a JSON string field is circular, unreliable (the LLM may truncate or paraphrase), and wastes output tokens. The agent sets this field directly from the truncated HTML string it passed to the LLM.

---

## How to Run

### Install dependencies

```bash
uv sync
uv run playwright install chromium
```

### Run tests

```bash
uv run pytest tests/ -v
```

### Run the full pipeline

```bash
uv run python orchestrator.py path/to/test_case.txt https://target-url.example.com
```

Prints `{ "analyst": {...}, "browser": {...} }` JSON to stdout.

### Run a single agent

```bash
# Analyst Agent only (no browser, no URL needed)
uv run python orchestrator.py --analyst-only path/to/test_case.txt

# Browser Agent only (no test case needed)
uv run python orchestrator.py --browser-only https://target-url.example.com
```

Each flag is mutually exclusive. Future agents follow the same pattern: add a
`run_<agent>()` top-level function in `orchestrator.py` and wire it to a
`--<agent>-only` flag.

### Run linters

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright llm/ agents/ tools/ agent_base.py orchestrator.py
```

---

## Dependencies Installed (Phase 2)

New additions to Phase 1:

```
Package     Version
----------- -------
greenlet    3.5.0
playwright  1.59.0
pyee        13.0.1
```

---

## Environment

- **OS:** Windows 11 Pro (10.0.26200)
- **Python:** 3.14.4
- **uv:** 0.11.10 (x86_64-pc-windows-msvc)
- **Shell used:** bash (Git Bash / Claude Code terminal)

### `.env.example` contents

```
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
LLM_PROVIDER=anthropic
DEBUG_SCREENSHOTS=
```

Copy `.env.example` to `.env` and populate `ANTHROPIC_API_KEY` before running tests or the orchestrator. Set `DEBUG_SCREENSHOTS=true` to save screenshots of each navigated page to `output/screenshots/`.
