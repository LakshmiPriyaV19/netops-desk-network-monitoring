"""REST API endpoints for dashboard summary metrics and simulated monitoring controls."""

from flask import Blueprint, current_app, jsonify, request

from app.models import (
    DEVICE_STATUSES,
    INCIDENT_PRIORITIES,
    INCIDENT_STATUSES,
    Device,
    Incident,
)
from app.services.monitoring import run_monitoring_cycle
from app.services.seeder import seed_demo_data

dashboard_bp = Blueprint("api_dashboard", __name__, url_prefix="/api")


@dashboard_bp.get("/dashboard")
def get_dashboard_summary():
    """Return aggregated device health, incident breakdown, and simulation metadata."""
    devices = Device.query.all()
    incidents = Incident.query.all()

    device_status_counts = {status: 0 for status in DEVICE_STATUSES}
    device_type_counts: dict[str, int] = {}
    latencies: list[float] = []
    uptimes: list[float] = []

    for device in devices:
        device_status_counts[device.status] = device_status_counts.get(device.status, 0) + 1
        device_type_counts[device.device_type] = device_type_counts.get(device.device_type, 0) + 1
        if device.simulated_latency_ms is not None:
            latencies.append(device.simulated_latency_ms)
        uptimes.append(device.simulated_uptime_pct)

    incident_status_counts = {status: 0 for status in INCIDENT_STATUSES}
    incident_priority_counts = {priority: 0 for priority in INCIDENT_PRIORITIES}
    open_priority_counts = {priority: 0 for priority in INCIDENT_PRIORITIES}

    for incident in incidents:
        incident_status_counts[incident.status] = incident_status_counts.get(incident.status, 0) + 1
        incident_priority_counts[incident.priority] = incident_priority_counts.get(incident.priority, 0) + 1
        if incident.status != "RESOLVED":
            open_priority_counts[incident.priority] = open_priority_counts.get(incident.priority, 0) + 1

    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else None
    avg_uptime = round(sum(uptimes) / len(uptimes), 2) if uptimes else 100.0

    last_checked_timestamps = [d.last_checked for d in devices if d.last_checked is not None]
    last_cycle_at = (
        max(last_checked_timestamps).isoformat() if last_checked_timestamps else None
    )

    return jsonify({
        "devices": {
            "total": len(devices),
            "online": device_status_counts["ONLINE"],
            "offline": device_status_counts["OFFLINE"],
            "warning": device_status_counts["WARNING"],
            "avg_simulated_latency_ms": avg_latency,
            "avg_simulated_uptime_pct": avg_uptime,
            "by_type": device_type_counts,
        },
        "incidents": {
            "total": len(incidents),
            "open": incident_status_counts["OPEN"],
            "in_progress": incident_status_counts["IN_PROGRESS"],
            "resolved": incident_status_counts["RESOLVED"],
            "active_open_total": incident_status_counts["OPEN"] + incident_status_counts["IN_PROGRESS"],
            "by_priority": incident_priority_counts,
            "active_by_priority": open_priority_counts,
        },
        "monitoring": {
            "simulated": True,
            "disclaimer": "All device health checks, latency, and uptime metrics are simulated by Python for demonstration purposes.",
            "enabled": current_app.config.get("MONITORING_ENABLED", False),
            "interval_seconds": current_app.config.get("MONITORING_INTERVAL_SECONDS", 15),
            "last_cycle_at": last_cycle_at,
        },
    }), 200


@dashboard_bp.post("/monitoring/run")
def trigger_monitoring_cycle():
    """Manually execute one simulated network monitoring cycle."""
    data = request.get_json(silent=True) or {}
    auto_incidents = bool(data.get("auto_create_incidents", True))
    summary = run_monitoring_cycle(auto_create_incidents=auto_incidents)
    return jsonify(summary), 200


@dashboard_bp.post("/monitoring/seed")
def trigger_demo_seed():
    """Seed sample devices and incidents when the database is empty."""
    result = seed_demo_data()
    return jsonify({
        "message": "Demo inventory seeded." if result["devices_created"] else "Database already contains devices.",
        **result,
    }), 201 if result["devices_created"] else 200
