"""Shared fixtures for apps.llm tests."""
import pytest

from apps.llm.tests.factories import make_job


@pytest.fixture
def job(db):
    """Generic LLMJob to attach LLMCalls to. Tests that exercise run_prompt
    pass this in via the `job=` kwarg — run_prompt requires a job."""
    return make_job()
