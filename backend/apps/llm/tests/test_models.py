import pytest

from apps.llm.models import Prompt, PromptVersion


@pytest.mark.django_db
def test_prompt_version_autoincrements_per_prompt():
    p = Prompt.objects.create(key="x", name="X", consumer="c")
    v1 = PromptVersion.objects.create(prompt=p, body="v1")
    v2 = PromptVersion.objects.create(prompt=p, body="v2")
    assert (v1.version, v2.version) == (1, 2)


@pytest.mark.django_db
def test_prompt_version_autoincrement_independent_per_prompt():
    a = Prompt.objects.create(key="a", name="A", consumer="c")
    b = Prompt.objects.create(key="b", name="B", consumer="c")
    PromptVersion.objects.create(prompt=a, body="va1")
    PromptVersion.objects.create(prompt=a, body="va2")
    vb1 = PromptVersion.objects.create(prompt=b, body="vb1")
    assert vb1.version == 1


@pytest.mark.django_db
def test_save_prompt_version_does_not_auto_activate():
    p = Prompt.objects.create(key="x", name="X", consumer="c")
    v1 = PromptVersion.objects.create(prompt=p, body="v1")
    assert p.active_version_id is None  # explicit set required
    p.active_version = v1
    p.save()
    p.refresh_from_db()
    assert p.active_version_id == v1.pk


@pytest.mark.django_db
def test_prompt_version_unique_per_prompt():
    p = Prompt.objects.create(key="x", name="X", consumer="c")
    PromptVersion.objects.create(prompt=p, body="v1", version=1)
    with pytest.raises(Exception):
        PromptVersion.objects.create(prompt=p, body="dup", version=1)
