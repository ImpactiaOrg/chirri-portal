import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.llm.models import LLMJob
from apps.llm.tests.factories import make_call, make_job, make_prompt


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        email="su-llm-jobs@x.com", password="pass",
    )


@pytest.fixture
def staff(db):
    return get_user_model().objects.create_user(
        email="staff-llm@x.com", password="pass", is_staff=True,
    )


@pytest.mark.django_db
def test_jobs_changelist_renders(client, superuser):
    job = make_job(status=LLMJob.Status.SUCCESS)
    client.force_login(superuser)
    resp = client.get(reverse("admin:llm_llmjob_changelist"))
    assert resp.status_code == 200
    assert str(job.pk).encode() in resp.content


@pytest.mark.django_db
def test_calls_changelist_only_for_superuser(client, staff):
    """LLMCall.view permission is restricted to superuser by spec."""
    client.force_login(staff)
    resp = client.get(reverse("admin:llm_llmcall_changelist"))
    assert resp.status_code in (302, 403)


@pytest.mark.django_db
def test_calls_changelist_visible_to_superuser(client, superuser):
    prompt = make_prompt()
    job = make_job()
    make_call(job=job, prompt_version=prompt.active_version)
    client.force_login(superuser)
    resp = client.get(reverse("admin:llm_llmcall_changelist"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_status_endpoint_returns_json_with_progress(client, superuser):
    job = make_job(status=LLMJob.Status.RUNNING)
    prompt = make_prompt()
    make_call(job=job, prompt_version=prompt.active_version)
    client.force_login(superuser)
    resp = client.get(reverse("admin:llm_llmjob_status", args=[job.pk]))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "RUNNING"
    assert payload["calls_count"] == 1
    assert "total_cost_usd" in payload


@pytest.mark.django_db
def test_status_page_renders_for_superuser(client, superuser):
    job = make_job()
    client.force_login(superuser)
    resp = client.get(reverse("admin:llm_llmjob_change", args=[job.pk]))
    assert resp.status_code == 200
    # Custom template includes the poll script marker.
    assert b"data-llm-job-status" in resp.content
