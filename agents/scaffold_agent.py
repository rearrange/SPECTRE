"""ScaffoldAgent — Phase 6: generates an opinionated Playwright TS project scaffold."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, override

from agent_base import BaseAgent
from errors import ScaffoldError
from llm.base import LLMProvider

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_BASE = Path(__file__).parent.parent / "output" / "scaffolded"

# ---------------------------------------------------------------------------
# File content templates
# ---------------------------------------------------------------------------

_PLAYWRIGHT_CONFIG = """\
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  retries: 2,
  reporter: 'html',
  use: {
    baseURL: process.env.BASE_URL,
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
});
"""

_TSCONFIG = {
    "compilerOptions": {
        "strict": True,
        "target": "ES2022",
        "module": "commonjs",
        "esModuleInterop": True,
        "outDir": "./dist",
    },
    "include": ["**/*.ts"],
}

_BASE_PAGE_TS = """\
import { Page } from '@playwright/test';

export abstract class BasePage {
  constructor(protected readonly page: Page) {}
  abstract navigate(): Promise<void>;
}
"""

_FIXTURES_INDEX_TS = """\
import { test as base, expect } from '@playwright/test';

export const test = base;
export { expect };
"""

_AUTH_HELPER_TS = """\
import { Page } from '@playwright/test';

export async function login(page: Page, username: string, password: string): Promise<void> {
  // TODO: implement
}
"""

_GITIGNORE = """\
node_modules/
playwright-report/
test-results/
.env
dist/
"""

_GITLAB_CI = """\
stages:
  - test

test:
  stage: test
  script:
    - npm ci
    - npx playwright install --with-deps chromium
    - npm test
"""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ScaffoldResult:
    project_name: str
    project_root: str
    created_files: list[str]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ScaffoldAgent(BaseAgent):
    """Generates a complete opinionated Playwright TypeScript project on disk.

    Makes no LLM calls — pure file generation.
    """

    def __init__(self, llm: LLMProvider) -> None:
        super().__init__(llm)
        self._output_base: Path = _DEFAULT_OUTPUT_BASE

    @override
    def run(self, input: dict[str, Any]) -> dict[str, Any]:
        project_name: str = input["project_name"]
        project_root = self._output_base / project_name

        if project_root.exists():
            raise ScaffoldError(
                f"Project directory already exists: {project_root}. "
                "Remove it or use a different project name."
            )

        logger.info("[%s] Scaffolding project '%s' at %s", self._name, project_name, project_root)

        created: list[str] = []

        def write(rel: str, content: str) -> None:
            path = project_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            created.append(rel)

        def touch(rel: str) -> None:
            path = project_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            created.append(rel)

        # Directories with .gitkeep
        touch("tests/e2e/.gitkeep")
        touch("tests/smoke/.gitkeep")
        touch("test-data/.gitkeep")

        # TypeScript source files
        write("pages/base.page.ts", _BASE_PAGE_TS)
        write("fixtures/index.ts", _FIXTURES_INDEX_TS)
        write("helpers/auth.helper.ts", _AUTH_HELPER_TS)

        # Config files
        write("playwright.config.ts", _PLAYWRIGHT_CONFIG)
        write("tsconfig.json", json.dumps(_TSCONFIG, indent=2) + "\n")
        write(
            "package.json",
            json.dumps(
                {
                    "name": project_name,
                    "version": "1.0.0",
                    "scripts": {
                        "test": "playwright test",
                        "test:smoke": "playwright test tests/smoke",
                        "test:e2e": "playwright test tests/e2e",
                    },
                    "devDependencies": {
                        "@playwright/test": "^1.40.0",
                    },
                },
                indent=2,
            )
            + "\n",
        )
        write(".gitignore", _GITIGNORE)
        write(".gitlab-ci.yml", _GITLAB_CI)

        result = ScaffoldResult(
            project_name=project_name,
            project_root=str(project_root),
            created_files=created,
        )
        logger.info("[%s] Created %d files under %s", self._name, len(created), project_root)
        return {
            "project_name": result.project_name,
            "project_root": result.project_root,
            "created_files": result.created_files,
        }
