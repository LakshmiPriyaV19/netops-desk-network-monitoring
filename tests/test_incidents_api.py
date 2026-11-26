"""API tests for /api/incidents and /api/dashboard endpoints."""


def test_create_incident_and_dashboard_counts(client, sample_device):
    """POST /api/incidents creates an incident linked to a device and updates dashboard totals."""
    resp = client.post("/api/incidents", json={
        "device_id": sample_device.id,
        "title": "High CPU Utilization",
        "description": "Simulated CPU spike above 90%.",
        "priority": "CRITICAL",
    })
    assert resp.status_code == 201
    incident = resp.get_json()["incident"]
    assert incident["device_id"] == sample_device.id
    assert incident["device_name"] == sample_device.name
    assert incident["status"] == "OPEN"
    assert incident["priority"] == "CRITICAL"

    dash_resp = client.get("/api/dashboard")
    assert dash_resp.status_code == 200
    dash = dash_resp.get_json()
    assert dash["devices"]["total"] == 1
    assert dash["devices"]["online"] == 1
    assert dash["incidents"]["open"] == 1
    assert dash["incidents"]["by_priority"]["CRITICAL"] == 1
    assert dash["monitoring"]["simulated"] is True


def test_create_incident_missing_device_returns_404(client):
    """POST /api/incidents returns 404 when referencing a non-existent device."""
    resp = client.post("/api/incidents", json={
        "device_id": 9999,
        "title": "Orphan Incident",
        "priority": "LOW",
    })
    assert resp.status_code == 404


def test_update_and_resolve_incident(client, sample_incident):
    """PUT and POST /resolve transition incident states and manage resolved_at."""
    in_prog = client.put(f"/api/incidents/{sample_incident.id}", json={
        "status": "IN_PROGRESS",
        "priority": "CRITICAL",
    })
    assert in_prog.status_code == 200
    assert in_prog.get_json()["incident"]["status"] == "IN_PROGRESS"
    assert in_prog.get_json()["incident"]["resolved_at"] is None

    resolved = client.post(f"/api/incidents/{sample_incident.id}/resolve")
    assert resolved.status_code == 200
    res_data = resolved.get_json()["incident"]
    assert res_data["status"] == "RESOLVED"
    assert res_data["resolved_at"] is not None


def test_delete_incident(client, sample_incident):
    """DELETE /api/incidents/<id> removes the incident."""
    del_resp = client.delete(f"/api/incidents/{sample_incident.id}")
    assert del_resp.status_code == 200

    get_resp = client.get(f"/api/incidents/{sample_incident.id}")
    assert get_resp.status_code == 404
