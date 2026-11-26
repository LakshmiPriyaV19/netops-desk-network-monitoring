"""Tests for the web dashboard HTML route and static assets."""


def test_dashboard_page_renders_with_simulation_notice(client):
    """GET / serves the NetOps Desk dashboard with explicit simulation labels."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "NetOps Desk" in html
    assert "Simulated Monitoring Active" in html
    assert "deviceHealthChart" in html
    assert "incidentSeverityChart" in html
