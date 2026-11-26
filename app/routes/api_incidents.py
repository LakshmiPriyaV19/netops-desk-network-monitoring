"""REST API endpoints for managing network incidents."""

from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import INCIDENT_PRIORITIES, INCIDENT_STATUSES, Device, Incident
from app.services.validation import validate_incident_payload

incidents_bp = Blueprint("api_incidents", __name__, url_prefix="/api/incidents")


@incidents_bp.get("")
def list_incidents():
    """Return incidents ordered newest first with optional status, priority, and device filters."""
    query = Incident.query

    status = request.args.get("status")
    if status:
        upper_status = status.upper()
        if upper_status not in INCIDENT_STATUSES:
            return jsonify({
                "error": "Invalid status filter.",
                "allowed": list(INCIDENT_STATUSES),
            }), 400
        query = query.filter(Incident.status == upper_status)

    priority = request.args.get("priority")
    if priority:
        upper_priority = priority.upper()
        if upper_priority not in INCIDENT_PRIORITIES:
            return jsonify({
                "error": "Invalid priority filter.",
                "allowed": list(INCIDENT_PRIORITIES),
            }), 400
        query = query.filter(Incident.priority == upper_priority)

    device_id = request.args.get("device_id")
    if device_id:
        try:
            parsed_device_id = int(device_id)
        except ValueError:
            return jsonify({"error": "'device_id' query parameter must be an integer."}), 400
        query = query.filter(Incident.device_id == parsed_device_id)

    incidents = query.order_by(Incident.created_at.desc(), Incident.id.desc()).all()
    return jsonify({
        "incidents": [inc.to_dict() for inc in incidents],
        "count": len(incidents),
    }), 200


@incidents_bp.get("/<int:incident_id>")
def get_incident(incident_id: int):
    """Return a single incident by ID."""
    incident = db.session.get(Incident, incident_id)
    if incident is None:
        return jsonify({"error": f"Incident with id {incident_id} not found."}), 404

    return jsonify({"incident": incident.to_dict()}), 200


@incidents_bp.post("")
def create_incident():
    """Create a new incident assigned to an existing device."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a valid JSON object."}), 400

    cleaned, errors = validate_incident_payload(data, partial=False)
    if errors:
        return jsonify({"error": "Validation failed.", "details": errors}), 400

    device = db.session.get(Device, cleaned["device_id"])
    if device is None:
        return jsonify({
            "error": f"Device with id {cleaned['device_id']} not found."
        }), 404

    status = cleaned.get("status", "OPEN")
    incident = Incident(
        device_id=device.id,
        title=cleaned["title"],
        description=cleaned.get("description", ""),
        priority=cleaned.get("priority", "MEDIUM"),
        status=status,
        resolved_at=datetime.now(timezone.utc) if status == "RESOLVED" else None,
    )

    db.session.add(incident)
    db.session.commit()

    return jsonify({
        "message": "Incident created successfully.",
        "incident": incident.to_dict(),
    }), 201


@incidents_bp.put("/<int:incident_id>")
def update_incident(incident_id: int):
    """Update incident attributes, reassignment, or resolution status."""
    incident = db.session.get(Incident, incident_id)
    if incident is None:
        return jsonify({"error": f"Incident with id {incident_id} not found."}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a valid JSON object."}), 400

    if not data:
        return jsonify({"error": "At least one updatable field must be provided."}), 400

    cleaned, errors = validate_incident_payload(data, partial=True)
    if errors:
        return jsonify({"error": "Validation failed.", "details": errors}), 400

    if "device_id" in cleaned:
        target_device = db.session.get(Device, cleaned["device_id"])
        if target_device is None:
            return jsonify({
                "error": f"Device with id {cleaned['device_id']} not found."
            }), 404
        incident.device_id = target_device.id

    if "title" in cleaned:
        incident.title = cleaned["title"]
    if "description" in cleaned:
        incident.description = cleaned["description"]
    if "priority" in cleaned:
        incident.priority = cleaned["priority"]

    if "status" in cleaned:
        new_status = cleaned["status"]
        if new_status == "RESOLVED":
            incident.mark_resolved()
        else:
            incident.status = new_status
            incident.resolved_at = None

    db.session.commit()

    return jsonify({
        "message": "Incident updated successfully.",
        "incident": incident.to_dict(),
    }), 200


@incidents_bp.route("/<int:incident_id>/resolve", methods=["POST", "PATCH"])
def resolve_incident(incident_id: int):
    """Convenience endpoint to resolve an incident immediately."""
    incident = db.session.get(Incident, incident_id)
    if incident is None:
        return jsonify({"error": f"Incident with id {incident_id} not found."}), 404

    incident.mark_resolved()
    db.session.commit()

    return jsonify({
        "message": "Incident marked as resolved.",
        "incident": incident.to_dict(),
    }), 200


@incidents_bp.delete("/<int:incident_id>")
def delete_incident(incident_id: int):
    """Delete an incident record."""
    incident = db.session.get(Incident, incident_id)
    if incident is None:
        return jsonify({"error": f"Incident with id {incident_id} not found."}), 404

    db.session.delete(incident)
    db.session.commit()

    return jsonify({
        "message": f"Incident {incident_id} deleted successfully.",
        "deleted_id": incident_id,
    }), 200
