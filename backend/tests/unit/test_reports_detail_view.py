import pytest

pytestmark = pytest.mark.django_db


class TestReportDetail:
    def _url(self, pk: int) -> str:
        return f"/api/reports/{pk}/"

    def test_returns_401_without_auth(self, api_client, balanz_published_report):
        res = api_client.get(self._url(balanz_published_report.pk))
        assert res.status_code == 401

    def test_returns_200_for_own_published_report(self, authed_balanz, balanz_published_report):
        res = authed_balanz.get(self._url(balanz_published_report.pk))
        assert res.status_code == 200
        assert res.data["id"] == balanz_published_report.pk
        assert res.data["brand_name"] == "Balanz"

    def test_returns_404_for_other_tenant(self, authed_rival, balanz_published_report):
        res = authed_rival.get(self._url(balanz_published_report.pk))
        assert res.status_code == 404

    def test_returns_404_for_draft(self, authed_balanz, balanz_published_report):
        from apps.reports.models import Report
        balanz_published_report.status = Report.Status.DRAFT
        balanz_published_report.save()
        res = authed_balanz.get(self._url(balanz_published_report.pk))
        assert res.status_code == 404

    def test_returns_404_for_unknown_id(self, authed_balanz):
        res = authed_balanz.get(self._url(99999))
        assert res.status_code == 404

    def test_response_shape_sections_widgets(self, authed_balanz, balanz_published_report):
        """Post-Task-8: report detail returns `sections` (not `blocks`) as the data surface.
        Legacy fields (`blocks`, `metrics`, `onelink`, `follower_snapshots`, etc.)
        are all gone — data lives inside typed widgets as snapshots."""
        res = authed_balanz.get(self._url(balanz_published_report.pk))
        assert res.status_code == 200
        assert "sections" in res.data
        for gone in ("blocks", "onelink", "follower_snapshots", "q1_rollup", "yoy", "metrics"):
            assert gone not in res.data, f"legacy field {gone} should be gone"
