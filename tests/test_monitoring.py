"""Stage 4 tests for simulated network monitoring and demo seeding."""

from app.extensions import db
from app.models import DEVICE_STATUSES, Device, Incident
from app.services.monitoring import run_monitoring_cycle


def test_monitoring_cycle_updates_devices_and_labels_simulated(app, sample_device):
    """run_monitoring_cycle updates last_checked, status, and simulated metrics."""
    previous_checked = sample_device.last_checked
    result = run_monitoring_cycle(auto_create_incidents=False, seed=42)

    assert result["simulated"] is True
    assert result["devices_checked"] == 1
    assert "simulated" in result["disclaimer"].lower()

    refreshed = db.session.get(Device, sample_device.id)
    assert refreshed.status in DEVICE_STATUSES
    assert refreshed.last_checked >= previous_checked
    assert 50.0 <= refreshed.simulated_uptime_pct <= 100.0
    if refreshed.status == "OFFLINE":
        assert refreshed.simulated_latency_ms is None
    else:
        assert refreshed.simulated_latency_ms is not None and refreshed.simulated_latency_ms > 0


def test_monitoring_cycle_api_endpoint_and_auto_incident(client, app):
    """POST /api/monitoring/run runs a simulated cycle and can raise alerts for OFFLINE devices."""
    # Seed 6 demo devices so at least one offline/transition path is exercised
    seed_resp = client.post("/api/monitoring/seed")
    assert seed_resp.status_code == 201
    assert seed_resp.get_json()["devices_created"] == 6

    run_resp = client.post("/api/monitoring/run", json={"auto_create_incidents": True})
    assert run_resp.status_code == 200
    body = run_resp.get_json()
    assert body["simulated"] is True
    assert body["devices_checked"] == 6


def test_seed_endpoint_is_idempotent(client):
    """Calling POST /api/monitoring/seed twice does not duplicate demo rows."""
    first = client.post("/api/monitoring/seed")
    assert first.status_code == 201
    assert first.get_json()["devices_created"] == 6

    second = client.post("/api/monitoring/seed")
    assert second.status_code == 200
    assert second.get_json()["devices_created"] == 0
    assert Device.query.count() == 6
    assert Incident.query.count() == 3
