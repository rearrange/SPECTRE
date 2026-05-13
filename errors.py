"""Shared exception types for SPECTRE agents."""


class RepoReaderError(Exception):
    """Raised when RepoReaderAgent fails to clone or analyse a repo."""


class ScaffoldError(Exception):
    """Raised when ScaffoldAgent fails to generate project structure."""
