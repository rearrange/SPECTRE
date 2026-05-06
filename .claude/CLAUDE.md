# CLAUDE.md — SPECTRE Project Context

## Project

- **Name:** SPECTRE
- **Description:** Multi-agent AI system that generates Playwright TypeScript test scripts from plain-text manual test case documents.
- **Current phase:** Phase 1 — Complete
- **Status:** All 7 tests passing. Linting (ruff) and type checking (basedpyright) fully clean.

---

## What Was Built in Phase 1

### File tree

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

### Deviations from original spec

| Item | Detail |
|------|--------|
| `ruff` added | Not in the Phase 1 spec. Added in a follow-up to enforce formatting and lint (E, F, I, UP, B, SIM rule sets). |
| `basedpyright` added | Not in the Phase 1 spec. Added in a follow-up to match the type checking Zed uses. Configured under `[tool.pyright]` in `pyproject.toml`. |
| `agents/__init__.py`, `llm/__init__.py`, `tests/__init__.py` | Not explicitly listed in the spec. Added as standard Python package markers required by setuptools discovery. |
| `output/.gitkeep` | Not in the spec. Added so the `output/` directory is tracked in git despite being gitignored for content. |
| `@override` on all method overrides | Added during basedpyright fix pass. Uses `typing.override` (stdlib in Python 3.12+, no extra dependency). |
| `_ = load_dotenv()` | `load_dotenv()` return value assigned to `_` to satisfy basedpyright's `reportUnusedCallResult`. |

### Python version and package manager confirmed working

- **Python:** 3.14.4
- **Package manager:** uv 0.11.10 (x86_64-pc-windows-msvc)

---

## Test Results

Final pytest run (verbatim terminal output):

```
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0 -- D:\Codes\GitLab\SPECTRE\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Codes\GitLab\SPECTRE
configfile: pyproject.toml
plugins: anyio-4.13.0, asyncio-1.3.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 7 items

tests/test_analyst_agent.py::test_analyst_extracts_title PASSED          [ 14%]
tests/test_analyst_agent.py::test_analyst_extracts_steps PASSED          [ 28%]
tests/test_analyst_agent.py::test_analyst_steps_have_required_fields PASSED [ 42%]
tests/test_analyst_agent.py::test_analyst_extracts_preconditions PASSED  [ 57%]
tests/test_analyst_agent.py::test_analyst_extracts_assertions PASSED     [ 71%]
tests/test_analyst_agent.py::test_analyst_returns_valid_json_structure PASSED [ 85%]
tests/test_analyst_agent.py::test_analyst_handles_search_test_case PASSED [100%]

============================= 7 passed in 31.36s ==============================
```

- **Total:** 7
- **Passed:** 7
- **Failed:** 0

Tests make live API calls to the Anthropic API (no mocking). Runtime is ~30s due to network latency.

---

## Key Implementation Decisions

### Choices not specified in the spec

**`AnalystParseError` as a named exception class**
Rather than raising a bare `ValueError`, a dedicated `AnalystParseError(Exception)` was introduced. This lets callers catch parse failures specifically without catching unrelated `ValueError`s from elsewhere in the stack.

**`_react_loop()` is a single-pass skeleton, not a real loop**
The spec called for a "ReAct loop." In Phase 1 the loop does exactly one think → act → observe cycle and returns. The structure is in place for Phase 2+ to add iterations, tool calls, and stop conditions — but nothing in Phase 1 required multiple passes.

**`input` parameter name kept despite shadowing the built-in**
The spec's method signature was `run(self, input: dict) -> dict`. The name was kept for readability and spec fidelity. ruff's `A002` (builtin-argument-shadowing) rule is not enabled, so this does not fail lint.

**`dict[str, Any]` for all agent input/output types**
The spec used bare `dict`. During the basedpyright fix pass all occurrences were tightened to `dict[str, Any]` from `typing` to satisfy `reportMissingTypeArgument`. Values are `Any` because agent inputs/outputs flow from JSON, which is inherently untyped.

**`TextBlock` narrowing in `AnthropicProvider.complete()`**
The original implementation used `message.content[0].text` directly. The Anthropic SDK types `content` as a union of many block types (TextBlock, ThinkingBlock, ToolUseBlock, etc.) — most of which have no `.text`. The fix uses `next(block for block in message.content if isinstance(block, TextBlock), None)` and raises `ValueError` if no text block is found. This is also correct at runtime when extended thinking is active and the first block is a ThinkingBlock.

**`load_dotenv()` called at module import time in `anthropic_provider.py`**
`load_dotenv()` runs when the module is first imported, not inside `__init__`. This means the `.env` file is loaded as a side effect of `import`. Acceptable for a CLI/script context; would need reconsideration for a library.

### Spec items interpreted differently

**`reportAny` and `reportUnknown*` suppressed in pyright config**
basedpyright's `reportAny` and family fire on every variable that touches `json.loads()` return values, which are `Any` by the typeshed definition of `json.loads`. These rules cannot be satisfied without wrapping every parsed result in a `TypedDict`. They are suppressed in `[tool.pyright]` while all other checks remain active at `typeCheckingMode = "standard"`.

---

## How to Run

### Install dependencies

```bash
uv sync
```

### Run tests

```bash
uv run pytest tests/ -v
```

### Run the analyst manually

Pass any plain-text test case file as the argument:

```bash
uv run python orchestrator.py path/to/test_case.txt
```

The orchestrator prints the extracted JSON to stdout.

### Run linters

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright llm/ agents/ agent_base.py orchestrator.py
```

---

## Dependencies Installed

```
Package               Version   Editable project location
--------------------- --------- -------------------------
annotated-types       0.7.0
anthropic             0.99.0
anyio                 4.13.0
basedpyright          1.39.3
certifi               2026.4.22
colorama              0.4.6
distro                1.9.0
docstring-parser      0.18.0
h11                   0.16.0
httpcore              1.0.9
httpx                 0.28.1
idna                  3.13
iniconfig             2.3.0
jiter                 0.14.0
nodejs-wheel-binaries 24.15.0
packaging             26.2
pluggy                1.6.0
pydantic              2.13.3
pydantic-core         2.46.3
pygments              2.20.0
pytest                9.0.3
pytest-asyncio        1.3.0
python-dotenv         1.2.2
ruff                  0.15.12
sniffio               1.3.1
spectre               0.1.0     D:\Codes\GitLab\SPECTRE
typing-extensions     4.15.0
typing-inspection     0.4.2
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
```

Copy `.env.example` to `.env` and populate `ANTHROPIC_API_KEY` before running tests or the orchestrator. The key is validated at `AnthropicProvider.__init__()` and raises `ValueError` if missing.
