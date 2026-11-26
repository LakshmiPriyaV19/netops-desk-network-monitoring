"""Stage 2 tests verifying database models, relationships, and constraints."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Device, Incident


def test_device_creation_and_serialization(app):
    """Verify Device defaults, timestamps, and JSON serialization."""
    device = Device(
        name="edge-fw-01",
        ip_address="192.168.10.1",
        device_type="Firewall",
        location="Chennai-POP / Cage 2",
    )
    db.session.add(device)
    db.session.commit()

    payload = device.to_dict()
    assert payload["id"] is not None
    assert payload["status"] == "ONLINE"
    assert payload["metrics_simulated"] is True
    assert payload["last_checked"] is not None
    assert payload["open_incidents_count"] == 0


def test_device_unique_ip_constraint(app, sample_device):
    """Verify duplicate IP addresses are rejected by the database."""
    duplicate = Device(
        name="core-rtr-02",
        ip_address=sample_device.ip_address,
        device_type="Router",
        location="BLR-DC-1 / Rack A2",
    )
    db.session.add(duplicate)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_device_invalid_status_constraint(app):
    """Verify database CheckConstraint rejects invalid device statuses."""
    bad_device = Device(
        name="bad-sw-01",
        ip_address="10.0.0.99",
        device_type="Switch",
        location="Lab",
        status="UNKNOWN",
    )
    db.session.add(bad_device)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_incident_relationship_and_cascade_delete(app, sample_device, sample_incident):
    """Verify foreign key link and cascade deletion when parent device is deleted."""
    assert sample_incident.device_id == sample_device.id
    assert sample_device.incidents[0].id == sample_incident.id

    db.session.delete(sample_device)
    db.session.commit()

    assert Incident.query.count() == 0
