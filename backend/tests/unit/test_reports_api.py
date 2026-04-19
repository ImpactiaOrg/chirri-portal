"""reports/latest/ auth + 204-when-empty.

Regression: we used to return `Response(None)` when the user had no published
reports, which DRF's JSONRenderer serializes as an empty byte string (not the
string "null"). That made the frontend's `res.json()` throw
"Unexpected end of JSON input" and crashed the home page. Switched to
HTTP 204 for the empty case; the frontend's apiFetch turns 204 into
`undefined`, which the home page treats as "no report yet".
"""
import pytest


@pytest.mark.django_db
class TestLatestReport:
    url = "/api/reports/latest/"

    def test_anonymous_is_401(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == 401

    def test_no_published_reports_returns_204(self, authed_balanz):
        response = authed_balanz.get(self.url)
        assert response.status_code == 204
        # Body must be empty; the 204 path is how the frontend detects "no report".
        assert response.content == b""

    def test_returns_latest_published_report(
        self, authed_balanz, balanz_published_report
    ):
        response = authed_balanz.get(self.url)
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == balanz_published_report.id
        assert body["title"] == "Reporte mensual de prueba"
        assert body["status"] == "PUBLISHED"
        assert len(body["metrics"]) == 1
        assert body["metrics"][0]["metric_name"] == "reach"

    def test_does_not_leak_other_tenants_reports(
        self, authed_rival, balanz_published_report
    ):
        response = authed_rival.get(self.url)
        assert response.status_code == 204
