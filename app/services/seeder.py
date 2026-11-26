"""Seed helper for populating realistic demo devices and incidents."""

from app.extensions import db
from app.models import Device, Incident
from app.models.device import utc_now

DEMO_DEVICES = [
    {
        "name": "palc-core-rtr-01",
        "ip_address": "10.10.0.1",
        "device_type": "Router",
        "location": "Bengaluru DC-1 / Rack A1",
        "status": "ONLINE",
        "simulated_latency_ms": 6.4,
        "simulated_uptime_pct": 99.99,
    },
    {
        "name": "palc-dist-sw-02",
        "ip_address": "10.10.1.12",
        "device_type": "Switch",
        "location": "Bengaluru DC-1 / Rack A4",
        "status": "ONLINE",
        "simulated_latency_ms": 9.8,
        "simulated_uptime_pct": 99.94,
    },
    {
        "name": "palc-edge-fw-01",
        "ip_address": "172.16.0.1",
        "device_type": "Firewall",
        "location": "Chennai POP / Cage 2",
        "status": "WARNING",
        "simulated_latency_ms": 118.5,
        "simulated_uptime_pct": 98.40,
    },
    {
        "name": "palc-cloud-lb-01",
        "ip_address": "10.20.4.10",
        "device_type": "Load Balancer",
        "location": "Mumbai Cloud Region / AZ-1",
        "status": "ONLINE",
        "simulated_latency_ms": 14.2,
        "simulated_uptime_pct": 99.91,
    },
    {
        "name": "palc-campus-ap-07",
        "ip_address": "192.168.40.27",
        "device_type": "Access Point",
        "location": "Bengaluru HQ / Floor 3",
        "status": "OFFLINE",
        "simulated_latency_ms": None,
        "simulated_uptime_pct": 92.15,
    },
    {
        "name": "palc-telemetry-srv-03",
        "ip_address": "10.30.8.50",
        "device_type": "Server",
        "location": "Hyderabad DR / Rack D2",
        "status": "ONLINE",
        "simulated_latency_ms": 19.6,
        "simulated_uptime_pct": 99.87,
    },
]


def seed_demo_data() -> dict[str, int]:
    """Insert sample devices and incidents if the inventory is currently empty."""
    if Device.query.count() > 0:
        return {"devices_created": 0, "incidents_created": 0}

    now = utc_now()
    created_devices: dict[str, Device] = {}

    for item in DEMO_DEVICES:
        device = Device(last_checked=now, **item)
        db.session.add(device)
        created_devices[item["name"]] = device

    db.session.flush()

    demo_incidents = [
        Incident(
            device_id=created_devices["palc-campus-ap-07"].id,
            title="[Simulated Alert] palc-campus-ap-07 unreachable",
            description="Simulated monitoring probe timed out on VLAN 40 wireless controller heartbeat.",
            priority="HIGH",
            status="OPEN",
        ),
        Incident(
            device_id=created_devices["palc-edge-fw-01"].id,
            title="Elevated packet latency on WAN-1 tunnel",
            description="Simulated RTT exceeded 100 ms threshold across IPsec gateway.",
            priority="CRITICAL",
            status="IN_PROGRESS",
        ),
        Incident(
            device_id=created_devices["palc-core-rtr-01"].id,
            title="Scheduled BGP policy verification",
            description="Routine simulated route-map audit completed without packet drops.",
            priority="LOW",
            status="RESOLVED",
            resolved_at=now,
        ),
    ]

    db.session.add_all(demo_incidents)
    db.session.commit()

    return {
        "devices_created": len(created_devices),
        "incidents_created": len(demo_incidents),
    }
