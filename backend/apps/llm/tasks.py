"""Celery tasks for apps.llm.

run_llm_job: resolve and execute a consumer handler.
mark_stuck_jobs_as_failed: scheduled cleanup of RUNNING jobs > 10min.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.utils.module_loading import import_string

from .models import LLMJob

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0)
def run_llm_job(self, job_id: int) -> None:
    """Resolve LLMJob.handler_path and run it. Retry policy is inside services."""
    try:
        job = LLMJob.objects.get(pk=job_id)
    except LLMJob.DoesNotExist:
        logger.error("llm.job_not_found", extra={"job_id": job_id})
        return

    job.status = LLMJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    try:
        handler = import_string(job.handler_path)
        handler(job)
        job.refresh_from_db()
        job.status = LLMJob.Status.SUCCESS
    except Exception as exc:  # noqa: BLE001 — capture all to mark FAILED
        logger.exception("llm.job_failed", extra={
            "job_id": job_id, "consumer": job.consumer,
        })
        job.refresh_from_db()
        job.status = LLMJob.Status.FAILED
        job.error_message = f"{type(exc).__name__}: {exc}"
    finally:
        job.finished_at = timezone.now()
        job.save()


@shared_task
def mark_stuck_jobs_as_failed(threshold_minutes: int = 10) -> int:
    """Beat task: mark RUNNING jobs older than `threshold_minutes` as FAILED."""
    cutoff = timezone.now() - timedelta(minutes=threshold_minutes)
    qs = LLMJob.objects.filter(
        status=LLMJob.Status.RUNNING, started_at__lt=cutoff,
    )
    count = qs.count()
    qs.update(
        status=LLMJob.Status.FAILED,
        finished_at=timezone.now(),
        error_message=f"Job stuck > {threshold_minutes} minutes — auto-failed",
    )
    if count:
        logger.warning("llm.stuck_jobs_marked_failed", extra={"count": count})
    return count
