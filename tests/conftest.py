"""Shared pytest fixtures for NetOps Desk unit and API tests."""

import pytest

from app import create_app
from app.extensions import db
from app.models import Device, Incident


@pytest.fixture()
def app():
    """Create a fresh Flask application with an isolated in-memory database per test."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Return a Flask test client bound to the test application."""
    return app.test_client()


@pytest.fixture()
def sample_device(app):
    """Insert and return a sample network device for tests."""
    device = Device(
        name="core-rtr-01",
        ip_address="10.0.0.1",
        device_type="Router",
        location="BLR-DC-1 / Rack A1",
        status="ONLINE",
        simulated_latency_ms=8.4,
        simulated_uptime_pct=99.98,
    )
    db.session.add(device)
    db.session.commit()
    return device


@pytest.fixture()
def sample_incident(app, sample_device):
    """Insert and return a sample incident attached to sample_device."""
    incident = Incident(
        device_id=sample_device.id,
        title="BGP Flap on Uplink Interface",
        description="Simulated transient BGP peer reset observed.",
        priority="HIGH",
        status="OPEN",
    )
    db.session.add(incident)
    db.session.commit()
    return incident
