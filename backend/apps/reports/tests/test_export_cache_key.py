import pytest

from apps.reports.exports.cache_key import build_cache_key
from apps.reports.tests.factories import make_report


@pytest.mark.django_db
def test_cache_key_is_deterministic():
    r = make_report()
    assert build_cache_key(r) == build_cache_key(r)


@pytest.mark.django_db
def test_cache_key_changes_when_report_is_saved_again():
    import time
    r = make_report()
    k1 = build_cache_key(r)
    time.sleep(0.01)
    r.title = r.title + "!"
    r.save()
    r.refresh_from_db()
    assert build_cache_key(r) != k1


@pytest.mark.django_db
def test_cache_key_is_a_short_hex_string():
    r = make_report()
    k = build_cache_key(r)
    assert isinstance(k, str)
    assert len(k) == 16
    int(k, 16)  # parses as hex
