"""Synchronous git operation wrappers for SPECTRE."""

import os
import shutil
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from git import Repo

from errors import GitAgentError


def init_repo(path: str) -> Repo:
    """Initialise a new git repository at path and return it."""
    return Repo.init(path)


def clone_repo(url: str, dest: str) -> Repo:
    """Clone the repository at url into dest and return the Repo."""
    return Repo.clone_from(url, dest)


def create_branch(repo: Repo, branch_name: str) -> None:
    """Create and check out a new branch in repo."""
    repo.git.checkout("-b", branch_name)


def copy_script_to_repo(script_path: str, repo_path: str, dest_subdir: str = "tests") -> str:
    """Copy script_path into {repo_path}/{dest_subdir}/ and return the relative path."""
    dest_dir = Path(repo_path) / dest_subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / Path(script_path).name
    shutil.copy2(script_path, dest_file)
    return str(Path(dest_subdir) / Path(script_path).name)


def stage_and_commit(repo: Repo, message: str) -> str:
    """Stage all changes, commit with message, and return the commit SHA."""
    repo.git.add(A=True)
    commit = repo.index.commit(message)
    return commit.hexsha


def push_branch(repo: Repo, branch_name: str, remote_name: str = "origin") -> None:
    """Push branch_name to remote_name."""
    repo.git.push(remote_name, branch_name)


def open_gitlab_mr(
    repo_url: str,
    branch_name: str,
    target_branch: str = "main",
    title: str = "",
) -> str:
    """Open a GitLab merge request and return the MR web URL.

    Reads GITLAB_TOKEN from environment — never accepts a token as a parameter.
    Raises GitAgentError if GITLAB_TOKEN is not set.
    """
    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        raise GitAgentError("GITLAB_TOKEN environment variable is not set")

    import gitlab

    parsed = urlparse(repo_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    project_path = parsed.path.lstrip("/").removesuffix(".git")

    gl = gitlab.Gitlab(url=base_url, private_token=token)
    project = gl.projects.get(project_path)
    mr = project.mergerequests.create(
        {
            "source_branch": branch_name,
            "target_branch": target_branch,
            "title": title or f"feat(spectre): {branch_name}",
        }
    )
    return str(mr.web_url)


def open_github_pr(
    repo_url: str,
    branch_name: str,
    target_branch: str = "main",
    title: str = "",
) -> str:
    """GitHub PR stub — not yet implemented."""
    raise NotImplementedError("GitHub PR support not yet implemented")


def detect_provider(repo_url: str) -> Literal["gitlab", "github", "unknown"]:
    """Return the git hosting provider inferred from repo_url."""
    if "gitlab.com" in repo_url:
        return "gitlab"
    if "github.com" in repo_url:
        return "github"
    return "unknown"
