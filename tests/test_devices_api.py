"""API tests for /api/devices endpoints."""


def test_list_devices_empty(client):
    """GET /api/devices returns an empty list initially."""
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["devices"] == []
    assert data["count"] == 0


def test_create_device_success(client):
    """POST /api/devices registers a valid device and returns 201."""
    payload = {
        "name": "dist-sw-01",
        "ip_address": "10.10.2.15",
        "device_type": "Switch",
        "location": "BLR-DC-1 / Rack B3",
        "status": "ONLINE",
    }
    resp = client.post("/api/devices", json=payload)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["device"]["name"] == "dist-sw-01"
    assert body["device"]["ip_address"] == "10.10.2.15"
    assert body["device"]["metrics_simulated"] is True


def test_create_device_validation_errors(client):
    """POST /api/devices rejects invalid IP addresses and missing fields with 400."""
    resp = client.post("/api/devices", json={
        "name": "",
        "ip_address": "999.999.1.1",
        "device_type": "QuantumModem",
        "location": "Unknown",
    })
    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert "name" in details
    assert "ip_address" in details
    assert "device_type" in details


def test_create_duplicate_device_conflict(client, sample_device):
    """POST /api/devices returns 409 Conflict for duplicate IP or device name."""
    resp = client.post("/api/devices", json={
        "name": "new-rtr-99",
        "ip_address": sample_device.ip_address,
        "device_type": "Router",
        "location": "Mumbai-POP",
    })
    assert resp.status_code == 409


def test_update_and_delete_device(client, sample_device):
    """PUT and DELETE /api/devices/<id> update and remove the device."""
    put_resp = client.put(f"/api/devices/{sample_device.id}", json={
        "status": "WARNING",
        "location": "BLR-DC-2 / Rack C1",
    })
    assert put_resp.status_code == 200
    updated = put_resp.get_json()["device"]
    assert updated["status"] == "WARNING"
    assert updated["location"] == "BLR-DC-2 / Rack C1"

    del_resp = client.delete(f"/api/devices/{sample_device.id}")
    assert del_resp.status_code == 200

    get_resp = client.get(f"/api/devices/{sample_device.id}")
    assert get_resp.status_code == 404


def test_filter_devices_by_status_and_search(client, sample_device):
    """GET /api/devices supports status and search query parameters."""
    client.post("/api/devices", json={
        "name": "edge-fw-02",
        "ip_address": "172.16.5.10",
        "device_type": "Firewall",
        "location": "Pune-Office",
        "status": "OFFLINE",
    })

    offline_resp = client.get("/api/devices?status=OFFLINE")
    assert offline_resp.status_code == 200
    assert offline_resp.get_json()["count"] == 1
    assert offline_resp.get_json()["devices"][0]["name"] == "edge-fw-02"

    search_resp = client.get("/api/devices?search=core-rtr")
    assert search_resp.status_code == 200
    assert search_resp.get_json()["count"] == 1
