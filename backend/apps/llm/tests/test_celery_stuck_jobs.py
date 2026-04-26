from datetime import timedelta

import pytest
from django.utils import timezone

from apps.llm.models import LLMJob
from apps.llm.tasks import mark_stuck_jobs_as_failed
from apps.llm.tests.factories import make_job


@pytest.mark.django_db
def test_marks_running_jobs_older_than_threshold():
    fresh = make_job(status=LLMJob.Status.RUNNING)
    fresh.started_at = timezone.now() - timedelta(minutes=2)
    fresh.save()

    stuck = make_job(status=LLMJob.Status.RUNNING)
    stuck.started_at = timezone.now() - timedelta(minutes=15)
    stuck.save()

    count = mark_stuck_jobs_as_failed(threshold_minutes=10)

    assert count == 1
    fresh.refresh_from_db()
    stuck.refresh_from_db()
    assert fresh.status == LLMJob.Status.RUNNING
    assert stuck.status == LLMJob.Status.FAILED
    assert "auto-failed" in stuck.error_message


@pytest.mark.django_db
def test_does_not_touch_pending_or_success_or_failed_jobs():
    pending = make_job(status=LLMJob.Status.PENDING)
    success = make_job(status=LLMJob.Status.SUCCESS)
    failed = make_job(status=LLMJob.Status.FAILED)
    for j in (pending, success, failed):
        j.started_at = timezone.now() - timedelta(hours=1)
        j.save()

    mark_stuck_jobs_as_failed(threshold_minutes=10)

    pending.refresh_from_db()
    success.refresh_from_db()
    failed.refresh_from_db()
    assert pending.status == LLMJob.Status.PENDING
    assert success.status == LLMJob.Status.SUCCESS
    assert failed.status == LLMJob.Status.FAILED
