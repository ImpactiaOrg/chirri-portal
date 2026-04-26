from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.llm.models import LLMJob
from apps.llm.services import dispatch_job
from apps.llm.tasks import run_llm_job
from apps.llm.tests.factories import make_job


# Synchronous celery for tests.
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@pytest.mark.django_db
def test_dispatch_job_creates_pending_and_queues(monkeypatch):
    called = {}

    def fake_delay(job_id):
        called["job_id"] = job_id

    monkeypatch.setattr("apps.llm.services.run_llm_job.delay", fake_delay)

    job = dispatch_job(
        consumer="test.consumer",
        handler_path="apps.llm.tests.test_tasks._noop_handler",
        input_metadata={"a": 1},
    )
    assert job.status == LLMJob.Status.PENDING
    assert job.consumer == "test.consumer"
    assert called == {"job_id": job.pk}


def _noop_handler(job):
    job.output_metadata = {"ok": True}
    job.save()


def _failing_handler(job):
    raise RuntimeError("boom")


@pytest.mark.django_db
def test_run_llm_job_resolves_handler_and_marks_success():
    job = make_job(handler_path="apps.llm.tests.test_tasks._noop_handler")
    run_llm_job(job.pk)
    job.refresh_from_db()
    assert job.status == LLMJob.Status.SUCCESS
    assert job.output_metadata == {"ok": True}
    assert job.started_at is not None
    assert job.finished_at is not None


@pytest.mark.django_db
def test_run_llm_job_marks_failed_on_handler_exception():
    job = make_job(handler_path="apps.llm.tests.test_tasks._failing_handler")
    run_llm_job(job.pk)
    job.refresh_from_db()
    assert job.status == LLMJob.Status.FAILED
    assert "boom" in job.error_message
    assert job.finished_at is not None
