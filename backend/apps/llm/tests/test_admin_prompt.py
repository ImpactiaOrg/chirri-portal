import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.llm.models import Prompt, PromptVersion
from apps.llm.tests.factories import make_prompt


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        email="su-llm-admin@x.com", password="pass",
    )


@pytest.mark.django_db
def test_changelist_renders_for_superuser(client, superuser):
    make_prompt()
    client.force_login(superuser)
    resp = client.get(reverse("admin:llm_prompt_changelist"))
    assert resp.status_code == 200
    assert b"parse_pdf_report" in resp.content


@pytest.mark.django_db
def test_new_version_view_creates_inactive_version(client, superuser):
    p = make_prompt()
    client.force_login(superuser)
    resp = client.post(
        reverse("admin:llm_prompt_new_version", args=[p.pk]),
        {
            "body": "Updated body",
            "notes": "tweaked",
            "model_hint": "accounts/fireworks/models/kimi-k2p5",
            "response_format": "json_object",
            "json_schema": "",
        },
    )
    assert resp.status_code in (302, 303)
    p.refresh_from_db()
    assert p.versions.count() == 2
    new_v = p.versions.order_by("-version").first()
    assert new_v.body == "Updated body"
    # Did NOT auto-activate.
    assert p.active_version_id != new_v.pk


@pytest.mark.django_db
def test_set_active_updates_pointer(client, superuser):
    p = make_prompt()
    v2 = PromptVersion.objects.create(prompt=p, body="v2")
    client.force_login(superuser)
    resp = client.post(
        reverse("admin:llm_prompt_set_active", args=[p.pk, v2.pk])
    )
    assert resp.status_code in (302, 303)
    p.refresh_from_db()
    assert p.active_version_id == v2.pk


@pytest.mark.django_db
def test_diff_view_renders_html_diff(client, superuser):
    p = make_prompt(body="line one\nline two")
    v2 = PromptVersion.objects.create(prompt=p, body="line one\nline TWO")
    client.force_login(superuser)
    url = reverse("admin:llm_prompt_diff", args=[p.pk, p.active_version.pk, v2.pk])
    resp = client.get(url)
    assert resp.status_code == 200
    # difflib.HtmlDiff replaces spaces with &nbsp; in its HTML output.
    assert b"line&nbsp;two" in resp.content
    assert b"line&nbsp;TWO" in resp.content


@pytest.mark.django_db
def test_anon_blocked_from_admin(client):
    p = make_prompt()
    resp = client.get(reverse("admin:llm_prompt_changelist"))
    # Django redirects to login.
    assert resp.status_code == 302
