"""SQLAlchemy model representing a network incident linked to a device."""

from datetime import datetime, timezone
from sqlalchemy import CheckConstraint

from app.extensions import db
from app.models.device import utc_now, _format_dt

INCIDENT_PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
INCIDENT_STATUSES = ("OPEN", "IN_PROGRESS", "RESOLVED")


class Incident(db.Model):
    """Operational incident assigned to a registered network device."""

    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_incidents_priority",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')",
            name="ck_incidents_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True, default="")
    priority = db.Column(db.String(20), nullable=False, default="MEDIUM", index=True)
    status = db.Column(db.String(20), nullable=False, default="OPEN", index=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    device = db.relationship("Device", back_populates="incidents")

    def mark_resolved(self) -> None:
        """Transition incident to RESOLVED and record resolution timestamp."""
        self.status = "RESOLVED"
        if self.resolved_at is None:
            self.resolved_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Serialize the incident to a JSON-friendly dictionary."""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "device_name": self.device.name if self.device else None,
            "device_ip": self.device.ip_address if self.device else None,
            "title": self.title,
            "description": self.description or "",
            "priority": self.priority,
            "status": self.status,
            "created_at": _format_dt(self.created_at),
            "updated_at": _format_dt(self.updated_at),
            "resolved_at": _format_dt(self.resolved_at),
        }

    def __repr__(self) -> str:
        return (
            f"<Incident id={self.id} device_id={self.device_id} "
            f"priority={self.priority!r} status={self.status!r}>"
        )
