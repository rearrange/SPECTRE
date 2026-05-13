"""Phase 6 — RepoReaderAgent tests.

All Tier 1 tests use real git repos created in tmp_path via gitpython.
Only the LLM call (cypress_to_playwright_notes) is mocked.
"""

import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import git
import pytest

from agents.repo_reader_agent import RepoReaderAgent
from errors import RepoReaderError
from llm.base import LLMResponse

# ---------------------------------------------------------------------------
# Shared content for realistic .spec.ts files
# ---------------------------------------------------------------------------

_LOGIN_SPEC = """\
import { test, expect } from '@playwright/test';

test.describe('Login flow', () => {
  test('should display login form', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
  });

  test('should log in with valid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill('user@example.com');
    await page.getByLabel('Password').fill('secret');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill('bad@example.com');
    await page.getByLabel('Password').fill('wrong');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.getByRole('alert')).toContainText('Invalid credentials');
  });
});
"""

_CHECKOUT_SPEC = """\
import { test, expect } from '@playwright/test';
import { login } from '../helpers/auth.helper';

test.describe('Checkout', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'user@example.com', 'secret');
  });

  test('should complete purchase', async ({ page }) => {
    await page.goto('/cart');
    await page.getByRole('button', { name: 'Checkout' }).click();
    await page.getByLabel('Card number').fill('4242424242424242');
    await page.getByLabel('Expiry').fill('12/30');
    await page.getByLabel('CVC').fill('123');
    await page.getByRole('button', { name: 'Pay now' }).click();
    await expect(page.getByTestId('order-confirmation')).toBeVisible();
    await expect(page.getByText('Thank you for your order')).toBeVisible();
  });

  test('should show cart total', async ({ page }) => {
    await page.goto('/cart');
    const total = page.getByTestId('cart-total');
    await expect(total).toBeVisible();
  });
});
"""

_HOMEPAGE_SPEC = """\
import { test, expect } from '@playwright/test';

test('homepage loads', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/My App/);
  await expect(page.getByRole('navigation')).toBeVisible();
});
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _init_repo(path: Path) -> git.Repo:
    repo = git.Repo.init(path)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@example.com")
    return repo


@pytest.fixture
def playwright_local_repo(tmp_path: Path):
    """Real local git repo with a Playwright TS project structure."""
    repo_path = tmp_path / "fake-playwright-repo"
    repo_path.mkdir()

    (repo_path / "tests" / "e2e").mkdir(parents=True)
    (repo_path / "tests" / "smoke").mkdir(parents=True)
    (repo_path / "pages").mkdir()
    (repo_path / "helpers").mkdir()
    (repo_path / "fixtures").mkdir()

    (repo_path / "tests" / "e2e" / "login.spec.ts").write_text(_LOGIN_SPEC)
    (repo_path / "tests" / "e2e" / "checkout.spec.ts").write_text(_CHECKOUT_SPEC)
    (repo_path / "tests" / "smoke" / "homepage.spec.ts").write_text(_HOMEPAGE_SPEC)
    (repo_path / "pages" / "login.page.ts").write_text(
        "import { Page } from '@playwright/test';\nexport class LoginPage {}\n"
    )
    (repo_path / "helpers" / "auth.helper.ts").write_text(
        "export async function login(page: any, u: string, p: string) {}\n"
    )
    (repo_path / "fixtures" / "index.ts").write_text(
        "export { test, expect } from '@playwright/test';\n"
    )
    (repo_path / "playwright.config.ts").write_text(
        "import { defineConfig } from '@playwright/test';\n"
        "export default defineConfig({ testDir: './tests', retries: 1 });\n"
    )
    (repo_path / "tsconfig.json").write_text('{"compilerOptions": {"strict": true}}\n')
    (repo_path / "package.json").write_text(
        '{"name": "fake-repo", "devDependencies": {"@playwright/test": "^1.40.0"}}\n'
    )

    repo = _init_repo(repo_path)
    repo.git.add(A=True)
    repo.index.commit("initial commit")

    yield repo_path


@pytest.fixture
def cypress_local_repo(tmp_path: Path):
    """Real local git repo with a Cypress project structure."""
    repo_path = tmp_path / "fake-cypress-repo"
    repo_path.mkdir()

    (repo_path / "cypress" / "e2e").mkdir(parents=True)
    (repo_path / "cypress" / "support").mkdir(parents=True)

    (repo_path / "cypress.config.ts").write_text(
        "import { defineConfig } from 'cypress';\nexport default defineConfig({ e2e: { baseUrl: 'http://localhost:3000' } });\n"
    )
    (repo_path / "cypress" / "e2e" / "login.cy.ts").write_text(
        "describe('login', () => { it('loads', () => { cy.visit('/login'); cy.get('h1').should('exist'); }); });\n"
    )
    (repo_path / "cypress" / "support" / "commands.ts").write_text("// custom commands\n")
    (repo_path / "package.json").write_text(
        '{"name": "cypress-app", "devDependencies": {"cypress": "^13.0.0"}}\n'
    )

    repo = _init_repo(repo_path)
    repo.git.add(A=True)
    repo.index.commit("initial commit")

    yield repo_path


@pytest.fixture
def clone_output(tmp_path: Path) -> Path:
    """Temporary directory for clone output — isolated from real output/cloned_repos/."""
    base = tmp_path / "cloned_repos"
    base.mkdir()
    return base


def _agent(clone_output: Path, llm: Any = None) -> RepoReaderAgent:
    a = RepoReaderAgent(llm or MagicMock())
    a._clone_base = clone_output
    return a


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_clones_repo_and_extracts_folder_structure(
    playwright_local_repo: Path, clone_output: Path
) -> None:
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(playwright_local_repo)})
    assert isinstance(result["folder_structure"], dict)
    assert len(result["folder_structure"]) > 0
    assert "tests/" in result["folder_structure"] or any(
        k.startswith("tests") for k in result["folder_structure"]
    )


def test_detects_test_directory(playwright_local_repo: Path, clone_output: Path) -> None:
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(playwright_local_repo)})
    assert "tests" in result["tests_directory"]


def test_extracts_playwright_config(playwright_local_repo: Path, clone_output: Path) -> None:
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(playwright_local_repo)})
    assert result["playwright_config"] is not None
    assert "defineConfig" in result["playwright_config"]


def test_extracts_tsconfig(playwright_local_repo: Path, clone_output: Path) -> None:
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(playwright_local_repo)})
    assert result["tsconfig"] is not None


def test_extracts_package_json(playwright_local_repo: Path, clone_output: Path) -> None:
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(playwright_local_repo)})
    assert result["package_json"] is not None


def test_extracts_test_patterns(playwright_local_repo: Path, clone_output: Path) -> None:
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(playwright_local_repo)})
    patterns = result["test_patterns"]
    assert len(patterns) == 3
    for p in patterns:
        assert "file" in p
        assert "content" in p
        assert len(p["content"]) > 0


def test_detects_helper_utilities(playwright_local_repo: Path, clone_output: Path) -> None:
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(playwright_local_repo)})
    helpers = result["helper_utilities"]
    assert any("auth.helper.ts" in h for h in helpers)


def test_extracts_naming_conventions(playwright_local_repo: Path, clone_output: Path) -> None:
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(playwright_local_repo)})
    nc = result["naming_conventions"]
    assert "file_naming" in nc
    assert "test_suffix" in nc
    assert len(nc["file_naming"]) > 0
    assert len(nc["test_suffix"]) > 0


def test_is_not_cypress_repo(playwright_local_repo: Path, clone_output: Path) -> None:
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(playwright_local_repo)})
    assert result["is_cypress_repo"] is False
    assert result["cypress_to_playwright_notes"] is None


def test_cypress_repo_detection(cypress_local_repo: Path, clone_output: Path) -> None:
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(cypress_local_repo)})
    assert result["is_cypress_repo"] is True


def test_cypress_to_playwright_notes_generated(
    cypress_local_repo: Path, clone_output: Path
) -> None:
    llm = MagicMock()
    llm.complete.return_value = LLMResponse(
        content="Use page.goto() instead of cy.visit(); use getByRole() instead of cy.get().",
        model="mock",
        input_tokens=10,
        output_tokens=10,
    )
    agent = _agent(clone_output, llm)
    result = agent.run({"repo_url": str(cypress_local_repo)})
    assert result["is_cypress_repo"] is True
    assert result["cypress_to_playwright_notes"] is not None
    assert len(result["cypress_to_playwright_notes"]) > 0


def test_clone_is_idempotent(playwright_local_repo: Path, clone_output: Path) -> None:
    agent = _agent(clone_output)
    result1 = agent.run({"repo_url": str(playwright_local_repo)})
    result2 = agent.run({"repo_url": str(playwright_local_repo)})
    assert result1["clone_path"] == result2["clone_path"]


def test_clone_path_persists(playwright_local_repo: Path, clone_output: Path) -> None:
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(playwright_local_repo)})
    assert Path(result["clone_path"]).exists()


def test_invalid_url_raises_error(clone_output: Path) -> None:
    agent = _agent(clone_output)
    with pytest.raises(RepoReaderError):
        agent.run({"repo_url": "/nonexistent/path/that/does/not/exist"})


def test_cleanup_removes_clone(playwright_local_repo: Path, clone_output: Path) -> None:
    """After running the agent, the clone persists — verify manual cleanup works."""
    agent = _agent(clone_output)
    result = agent.run({"repo_url": str(playwright_local_repo)})
    clone_path = Path(result["clone_path"])
    assert clone_path.exists()

    shutil.rmtree(clone_path)
    assert not clone_path.exists()
