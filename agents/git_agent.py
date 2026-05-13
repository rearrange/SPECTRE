"""GitAgent — Phase 7: branch, commit, push, and open MR/PR."""

import logging
from typing import Any, override

import git

from agent_base import BaseAgent
from errors import GitAgentError
from llm.base import LLMProvider
from tools.git_tools import (
    copy_script_to_repo,
    create_branch,
    init_repo,
    open_gitlab_mr,
    push_branch,
    stage_and_commit,
)

logger = logging.getLogger(__name__)


class GitAgent(BaseAgent):
    """Deterministic git agent — no LLM calls.

    Flow A: open an existing repo, create a branch, copy the generated script,
            commit, push, and open a merge request.
    Flow B: init a new repo, copy the generated script, and commit (no push, no MR).
    """

    def __init__(self, llm: LLMProvider) -> None:
        super().__init__(llm)

    @override
    def run(self, input: dict[str, Any]) -> dict[str, Any]:
        flow: str = input["flow"]
        test_case_name: str = input["test_case_name"]
        script_path: str = input["script_path"]
        repo_path: str = input["repo_path"]

        if flow == "A":
            return self._run_flow_a(input, test_case_name, script_path, repo_path)
        return self._run_flow_b(test_case_name, script_path, repo_path)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_flow_a(
        self,
        input: dict[str, Any],
        test_case_name: str,
        script_path: str,
        repo_path: str,
    ) -> dict[str, Any]:
        repo_url: str | None = input.get("repo_url")
        if not repo_url:
            raise GitAgentError("Flow A requires repo_url in the input dict")

        branch_name = f"spectre/tc-{test_case_name}"
        commit_message = f"feat(spectre): add generated test for {test_case_name}"

        try:
            repo = git.Repo(repo_path)
            create_branch(repo, branch_name)
            copy_script_to_repo(script_path, repo_path)
            commit_sha = stage_and_commit(repo, commit_message)
            push_branch(repo, branch_name)
            mr_url = open_gitlab_mr(
                repo_url=repo_url,
                branch_name=branch_name,
                target_branch="main",
                title=commit_message,
            )
        except GitAgentError:
            raise
        except Exception as exc:
            raise GitAgentError(f"Flow A git operations failed: {exc}") from exc

        logger.info(
            "[%s] Flow A done — branch=%s commit=%s mr=%s",
            self._name,
            branch_name,
            commit_sha,
            mr_url,
        )
        return {
            "branch": branch_name,
            "commit_sha": commit_sha,
            "mr_url": mr_url,
            "status": "success",
        }

    def _run_flow_b(
        self,
        test_case_name: str,
        script_path: str,
        repo_path: str,
    ) -> dict[str, Any]:
        commit_message = f"feat(spectre): initial generated test for {test_case_name}"

        try:
            repo = init_repo(repo_path)
            copy_script_to_repo(script_path, repo_path)
            commit_sha = stage_and_commit(repo, commit_message)
        except Exception as exc:
            raise GitAgentError(f"Flow B git operations failed: {exc}") from exc

        logger.info(
            "[%s] Flow B done — commit=%s",
            self._name,
            commit_sha,
        )
        return {
            "branch": "main",
            "commit_sha": commit_sha,
            "mr_url": None,
            "status": "success",
        }
