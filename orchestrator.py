"""Orchestrator — stub that calls the AnalystAgent for Phase 1."""

import logging
from typing import Any

from agents.analyst_agent import AnalystAgent
from llm.anthropic_provider import AnthropicProvider

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


def run(test_case: str) -> dict[str, Any]:
    """Run the Phase 1 pipeline: Analyst only."""
    llm = AnthropicProvider()
    analyst = AnalystAgent(llm)
    logger.info("Orchestrator — running Analyst Agent")
    return analyst.run({"test_case": test_case})


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: uv run python orchestrator.py <test_case_file>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        raw = f.read()

    result = run(raw)
    import json

    print(json.dumps(result, indent=2))
