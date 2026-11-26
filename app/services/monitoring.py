"""Simulated network monitoring engine and background scheduler.

NOTE: This module intentionally SIMULATES network health checks, latency, and
uptime metrics using Python state transitions for portfolio demonstration.
It does NOT send real ICMP pings, SNMP polls, or live network traffic.
"""

import logging
import os
import random
import threading
from typing import Any

from flask import Flask

from app.extensions import db
from app.models import Device, Incident
from app.models.device import utc_now

logger = logging.getLogger(__name__)

# Weighted Markov transition table for realistic simulated device behavior
STATUS_TRANSITIONS: dict[str, tuple[tuple[str, ...], tuple[float, ...]]] = {
    "ONLINE": (("ONLINE", "WARNING", "OFFLINE"), (0.87, 0.10, 0.03)),
    "WARNING": (("ONLINE", "WARNING", "OFFLINE"), (0.45, 0.40, 0.15)),
    "OFFLINE": (("ONLINE", "WARNING", "OFFLINE"), (0.25, 0.25, 0.50)),
}

_scheduler_lock = threading.Lock()
_scheduler_started = False


def _simulate_device_metrics(
    device: Device,
    rng: random.Random,
) -> tuple[str, float | None, float]:
    """Compute the next simulated status, latency (ms), and uptime (%) for a device."""
    choices, weights = STATUS_TRANSITIONS.get(
        device.status,
        (("ONLINE", "WARNING", "OFFLINE"), (0.85, 0.10, 0.05)),
    )
    next_status = rng.choices(choices, weights=weights, k=1)[0]
    current_uptime = device.simulated_uptime_pct if device.simulated_uptime_pct is not None else 99.5

    if next_status == "ONLINE":
        base_latency = device.simulated_latency_ms if device.simulated_latency_ms and device.simulated_latency_ms < 50 else rng.uniform(6.0, 22.0)
        jitter = rng.uniform(-3.5, 4.5)
        next_latency = round(max(2.5, min(42.0, base_latency + jitter)), 2)
        next_uptime = round(min(100.0, current_uptime + rng.uniform(0.01, 0.05)), 2)
    elif next_status == "WARNING":
        next_latency = round(rng.uniform(75.0, 240.0), 2)
        next_uptime = round(max(82.0, current_uptime - rng.uniform(0.05, 0.20)), 2)
    else:  # OFFLINE
        next_latency = None
        next_uptime = round(max(50.0, current_uptime - rng.uniform(0.25, 0.75)), 2)

    return next_status, next_latency, next_uptime


def run_monitoring_cycle(
    auto_create_incidents: bool = True,
    seed: int | None = None,
) -> dict[str, Any]:
    """Run one simulated health-check sweep across all registered devices.

    Must be invoked inside a Flask application context.
    """
    rng = random.Random(seed) if seed is not None else random.Random()
    devices = Device.query.order_by(Device.id.asc()).all()
    checked_at = utc_now()

    status_changes: list[dict[str, Any]] = []
    incidents_auto_created = 0

    for device in devices:
        previous_status = device.status
        next_status, next_latency, next_uptime = _simulate_device_metrics(device, rng)

        device.status = next_status
        device.simulated_latency_ms = next_latency
        device.simulated_uptime_pct = next_uptime
        device.last_checked = checked_at

        if next_status != previous_status:
            status_changes.append({
                "device_id": device.id,
                "device_name": device.name,
                "from_status": previous_status,
                "to_status": next_status,
            })

            # Automatically raise a simulated incident when a device drops OFFLINE
            if auto_create_incidents and next_status == "OFFLINE":
                existing_open = Incident.query.filter(
                    Incident.device_id == device.id,
                    Incident.status != "RESOLVED",
                    Incident.title.like("[Simulated Alert]%"),
                ).first()
                if existing_open is None:
                    alert = Incident(
                        device_id=device.id,
                        title=f"[Simulated Alert] {device.name} unreachable",
                        description=(
                            f"Simulated monitoring cycle detected status transition from "
                            f"{previous_status} to OFFLINE for {device.ip_address} ({device.location})."
                        ),
                        priority="CRITICAL" if device.device_type in ("Router", "Firewall", "Load Balancer") else "HIGH",
                        status="OPEN",
                    )
                    db.session.add(alert)
                    incidents_auto_created += 1

    db.session.commit()

    return {
        "simulated": True,
        "disclaimer": "All health checks, latency, and uptime metrics are simulated by Python.",
        "checked_at": checked_at.isoformat(),
        "devices_checked": len(devices),
        "status_changes": status_changes,
        "incidents_auto_created": incidents_auto_created,
    }


def start_monitoring_scheduler(app: Flask) -> None:
    """Start the background daemon thread that runs periodic simulated checks."""
    global _scheduler_started

    if not app.config.get("MONITORING_ENABLED", False):
        return
    if app.config.get("TESTING", False):
        return

    # Prevent duplicate background threads when Flask's Werkzeug reloader is active
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True

    interval = max(5, int(app.config.get("MONITORING_INTERVAL_SECONDS", 15)))

    def _worker() -> None:
        stop_event = threading.Event()
        while not stop_event.wait(timeout=interval):
            try:
                with app.app_context():
                    run_monitoring_cycle(auto_create_incidents=True)
            except Exception as exc:  # pragma: no cover - defensive background logging
                logger.warning("Simulated monitoring cycle error: %s", exc)

    thread = threading.Thread(
        target=_worker,
        name="netops-simulated-monitor",
        daemon=True,
    )
    thread.start()
