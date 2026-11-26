"""SQLAlchemy model representing a monitored network device."""

from datetime import datetime, timezone
from sqlalchemy import CheckConstraint

from app.extensions import db

DEVICE_STATUSES = ("ONLINE", "OFFLINE", "WARNING")
DEVICE_TYPES = (
    "Router",
    "Switch",
    "Firewall",
    "Access Point",
    "Server",
    "Load Balancer",
)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _format_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


class Device(db.Model):
    """Network device inventory and latest simulated health telemetry."""

    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ONLINE', 'OFFLINE', 'WARNING')",
            name="ck_devices_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    ip_address = db.Column(db.String(45), nullable=False, unique=True, index=True)
    device_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="ONLINE", index=True)

    # Simulated monitoring metrics (explicitly marked as simulated in API responses & UI)
    simulated_latency_ms = db.Column(db.Float, nullable=True, default=12.5)
    simulated_uptime_pct = db.Column(db.Float, nullable=False, default=99.95)
    last_checked = db.Column(db.DateTime(timezone=True), nullable=True, default=utc_now)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # One-to-many relationship: deleting a device cascades to its incidents
    incidents = db.relationship(
        "Incident",
        back_populates="device",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def to_dict(self, include_incidents: bool = False) -> dict:
        """Serialize the device to a JSON-friendly dictionary."""
        open_incident_count = sum(
            1 for inc in self.incidents if inc.status != "RESOLVED"
        )
        data = {
            "id": self.id,
            "name": self.name,
            "ip_address": self.ip_address,
            "device_type": self.device_type,
            "location": self.location,
            "status": self.status,
            "simulated_latency_ms": (
                round(self.simulated_latency_ms, 2)
                if self.simulated_latency_ms is not None
                else None
            ),
            "simulated_uptime_pct": round(self.simulated_uptime_pct, 2),
            "metrics_simulated": True,
            "last_checked": _format_dt(self.last_checked),
            "created_at": _format_dt(self.created_at),
            "updated_at": _format_dt(self.updated_at),
            "open_incidents_count": open_incident_count,
        }
        if include_incidents:
            data["incidents"] = [inc.to_dict() for inc in self.incidents]
        return data

    def __repr__(self) -> str:
        return f"<Device id={self.id} name={self.name!r} ip={self.ip_address!r} status={self.status!r}>"
