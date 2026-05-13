# CLAUDE.md — SPECTRE Project Context

## Project

- **Name:** SPECTRE
- **Description:** Multi-agent AI system that generates Playwright TypeScript test scripts from plain-text manual test case documents.
- **Current phase:** Phase 6 — Complete
- **Status:** All 84 tests passing. Linting (ruff) and type checking (basedpyright) fully clean.

## Current File Tree

```
SPECTRE/
├── .env.example
├── .gitattributes
├── .gitignore
├── agent_base.py              # Abstract BaseAgent with ReAct loop skeleton
├── errors.py                  # Shared exception types: RepoReaderError, ScaffoldError
├── orchestrator.py            # Orchestrator class + Flow A/B routing + retry loop + CLI entry point
├── pyproject.toml
├── uv.lock
├── agents/
│   ├── __init__.py            # Exports all agents + their errors (incl. RepoReaderError, ScaffoldError)
│   ├── analyst_agent.py       # Extracts structured JSON from plain-text test cases
│   ├── browser_agent.py       # Navigates URL with Playwright, returns UI observation JSON
│   ├── coder_agent.py         # Takes Analyst + Browser JSON, generates Playwright TS .spec.ts; accepts optional reviewer_feedback
│   ├── reviewer_agent.py      # LLM-based reviewer: checks syntax, coverage, best practices; raises ReviewerError
│   ├── repo_reader_agent.py   # Clones Git repo, extracts folder tree + test patterns + config; one LLM call for Cypress notes
│   ├── scaffold_agent.py      # Generates opinionated PW TS project on disk; no LLM calls; raises ScaffoldError if exists
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
│   ├── test_reviewer_agent.py # 10 tests — ReviewerAgent contract (8 Tier 1 + 2 Tier 2 e2e)
│   ├── test_repo_reader_agent.py  # 15 tests — RepoReaderAgent contract (all Tier 1, real git)
│   ├── test_scaffold_agent.py     # 14 tests — ScaffoldAgent contract (all Tier 1)
│   └── test_orchestrator.py   # 18 tests — Orchestrator contract (15 Tier 1 + 3 Tier 2 e2e)
└── output/
    ├── .gitkeep               # Tracks gitignored output directory
    ├── cloned_repos/          # Persisted repo clones (created by RepoReaderAgent, gitignored)
    └── scaffolded/            # Scaffolded projects (created by ScaffoldAgent, gitignored)
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

### Key decisions

**`Orchestrator._run_browser()` is synchronous** — wraps the async Playwright flow in `asyncio.run()`, making `Orchestrator.run()` fully synchronous and easy to call from tests and the CLI without async ceremony.

**Agents created internally in `__init__`** — all agents share the same `LLMProvider` instance passed to the Orchestrator. No agent wiring needed at the call site.

**Retry loop uses `for/else`** — the `else` branch sets `retries = MAX_RETRIES - 1` when the loop exhausts without a PASS, matching the spec's contract exactly.

---

## Phase 5 — ReviewerAgent + Retry Loop

Replaces the `ReviewerAgent` stub with a real LLM-based reviewer. Wires the Orchestrator retry loop to pass full feedback back to `CoderAgent` for a targeted rewrite on `FAIL`.

### What changed

- **`agents/reviewer_agent.py`** — fully implemented LLM-based reviewer. Sends the script and analyst_output to Claude and returns a `{"verdict", "issues", "suggestions"}` dict. Raises `ReviewerError` on empty or unparseable response. Strips markdown code fences the LLM occasionally adds despite system prompt instructions.
- **`orchestrator.py`** — retry loop now re-calls `CoderAgent` on FAIL, passing `reviewer_feedback` in the coder input. After `MAX_RETRIES` exhausted, returns last state without raising.
- **`agents/coder_agent.py`** — optionally reads `reviewer_feedback` from input dict and appends formatted feedback block to the generation prompt. Backward-compatible; existing tests unaffected.
- **`agents/__init__.py`** — exports `ReviewerError`.
- **`tests/test_reviewer_agent.py`** — 10 new tests (8 Tier 1, 2 Tier 2 e2e).
- **`tests/test_orchestrator.py`** — 5 new tests (4 Tier 1, 1 Tier 2 e2e for forced-fail retry loop).

### Three review criteria

1. **Playwright TS syntax validity** — valid TypeScript, correct Playwright API usage
2. **Test coverage** — every step and assertion from `analyst_output` is represented
3. **Best practices** — proper `expect()` assertions, semantic locators (`getByRole`, `getByLabel`, `getByTestId`), no `waitForTimeout()` sleeps

### Deviations from spec

| Item | Detail |
|------|--------|
| Markdown fence stripping | LLM occasionally wraps response in ` ```json ``` ` despite system prompt. `ReviewerAgent` strips these before `json.loads()`. |
| `test_reviewer_stub_returns_pass_verdict` renamed | Original test tested stub behavior; renamed `test_reviewer_returns_verdict_dict` to test the real implementation with a mocked LLM. |
| `_make_orchestrator_with_stubs` always mocks reviewer | When `reviewer_side_effects=None`, reviewer is now mocked with a default PASS to prevent the real LLM from being called in basic unit tests. |

---

## Phase 6 — RepoReaderAgent + ScaffoldAgent

Replaces both Phase 4 stubs with real implementations. Wires `repo_context` from RepoReaderAgent into the Analyst prompt (Flow A). Orchestrator result dict now includes `repo_context` and `scaffold_result` fields.

### What changed

- **`errors.py`** (new) — `RepoReaderError` and `ScaffoldError` exception types.
- **`agents/repo_reader_agent.py`** — full implementation. Clones via `gitpython` into `output/cloned_repos/{name}/`. Extracts: folder tree (depth 4), naming conventions, test patterns (≤3 files × 50 lines), playwright/tsconfig/package.json, helper utilities, Cypress detection. One LLM call only for `cypress_to_playwright_notes`. Idempotent — skips re-clone if directory exists. Raises `RepoReaderError` on git failure.
- **`agents/scaffold_agent.py`** — full implementation. Generates 11-file opinionated PW TS scaffold under `output/scaffolded/{name}/`. No LLM calls. Raises `ScaffoldError` if project directory already exists.
- **`orchestrator.py`** — Flow A now calls real `RepoReaderAgent` and passes `repo_context` to `AnalystAgent`. Flow B now calls real `ScaffoldAgent` with optional `project_name` from input dict. Result dict includes `repo_context` and `scaffold_result` (both `None` if not applicable).
- **`agents/__init__.py`** — exports `RepoReaderError`, `ScaffoldError`.
- **`tests/test_repo_reader_agent.py`** (new) — 15 Tier 1 tests. Uses real `gitpython` repos in `tmp_path`; only LLM call is mocked.
- **`tests/test_scaffold_agent.py`** (new) — 14 Tier 1 tests. All output redirected to `tmp_path` via `agent._output_base`.
- **`tests/test_orchestrator.py`** — updated: `test_repo_reader_stub_returns_dict` and `test_scaffold_stub_returns_dict` replaced with real-implementation tests using `tmp_path`; `_make_orchestrator_with_stubs` now also mocks `_repo_reader.run` and `_scaffold.run`; e2e Flow A test mocks `_repo_reader.run` to avoid real network clone; 2 new Tier 1 integration tests added.
- **`pyproject.toml`** — `gitpython` added as a dependency.

### New agent: RepoReaderAgent

| Field | Source |
|---|---|
| `folder_structure` | `pathlib` traversal, depth ≤ 4, excludes `.git`, `node_modules`, `.venv` |
| `naming_conventions` | Counter-based suffix/pattern detection over all test files |
| `test_patterns` | First 50 lines of up to 3 `.spec.ts` / `.test.ts` files |
| `playwright_config` | Raw content of `playwright.config.ts` / `playwright.config.js` |
| `tsconfig`, `package_json` | Raw content if present |
| `helper_utilities` | Files under `helpers/`, `utils/`, `fixtures/`, `support/` |
| `is_cypress_repo` | Detects `cypress.config.*` or `cypress/` directory |
| `cypress_to_playwright_notes` | LLM call (only if `is_cypress_repo`) |
| `tests_directory` | Most common parent directory of test files |
| `clone_path` | Absolute path to persisted clone |

### New agent: ScaffoldAgent

Generated scaffold structure:

```
{project_name}/
├── tests/e2e/.gitkeep
├── tests/smoke/.gitkeep
├── pages/base.page.ts          # abstract class BasePage
├── fixtures/index.ts           # re-exports test + expect
├── helpers/auth.helper.ts      # login() stub that compiles
├── test-data/.gitkeep
├── playwright.config.ts        # Chromium, retries:2, baseURL from BASE_URL env
├── tsconfig.json               # strict:true, ES2022, commonjs
├── package.json                # @playwright/test, test/test:smoke/test:e2e scripts
├── .gitignore                  # node_modules, playwright-report, test-results, .env
└── .gitlab-ci.yml              # npm ci → playwright install chromium → npm test
```

### Deviations from spec

| Item | Detail |
|------|--------|
| `test_repo_reader_stub_returns_dict` renamed | Now `test_repo_reader_returns_dict`; uses a real local git repo in `tmp_path`. |
| `test_scaffold_stub_returns_dict` renamed | Now `test_scaffold_returns_dict`; uses `tmp_path` output redirect. |
| e2e Flow A test mocks `_repo_reader.run` | The test focuses on Analyst→Browser→Coder→Reviewer; real repo clone is out of scope for that e2e test. |

---

## Test Results

```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
collected 84 items

tests/test_analyst_agent.py         7 passed
tests/test_browser_agent.py         7 passed
tests/test_coder_agent.py          13 passed  (11 Tier 1 + 2 Tier 2 e2e)
tests/test_reviewer_agent.py       10 passed  (8 Tier 1 + 2 Tier 2 e2e)
tests/test_repo_reader_agent.py    15 passed  (all Tier 1)
tests/test_scaffold_agent.py       14 passed  (all Tier 1)
tests/test_orchestrator.py         18 passed  (15 Tier 1 + 3 Tier 2 e2e)

======================== 84 passed ========================
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
uv run pytest tests/ -v                                           # full suite
uv run pytest tests/ -v -m "not e2e"                             # Tier 1 only (fast)
uv run pytest tests/test_orchestrator.py -v -m "not e2e"         # Orchestrator Tier 1 only
uv run pytest tests/test_repo_reader_agent.py -v                 # RepoReaderAgent all tests
uv run pytest tests/test_scaffold_agent.py -v                    # ScaffoldAgent all tests
uv run pytest tests/test_orchestrator.py -v -m e2e               # Orchestrator Tier 2 e2e only
uv run pytest tests/test_reviewer_agent.py -v -m e2e             # Reviewer Tier 2 e2e only
```

### Pipeline

```bash
# Full pipeline — Flow B (new project, no repo)
uv run python orchestrator.py path/to/test_case.txt https://staging.example.com

# Full pipeline — Flow A (existing repo)
uv run python orchestrator.py path/to/test_case.txt https://staging.example.com https://gitlab.example.com/your/repo
```

Prints the full result JSON to stdout, followed by the generated `.spec.ts` content.

Output directories:
- `output/cloned_repos/` — persisted repo clones from Flow A (gitignored)
- `output/scaffolded/` — generated project scaffolds from Flow B (gitignored)

### Linters

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright llm/ agents/ agent_base.py orchestrator.py
```

---

## Next Phase

**Phase 7 — Git Agent**

Replace `GitAgent` stub with a real implementation that creates a branch, commits the generated `.spec.ts` file into the appropriate location (from `RepoContext.clone_path` for Flow A, or the scaffold root for Flow B), and opens a merge/pull request against the target repo.
