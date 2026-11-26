"""REST API endpoints for managing network devices."""

from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import DEVICE_STATUSES, Device
from app.models.device import utc_now
from app.services.validation import validate_device_payload

devices_bp = Blueprint("api_devices", __name__, url_prefix="/api/devices")


@devices_bp.get("")
def list_devices():
    """Return all registered devices with optional status, type, and search filtering."""
    query = Device.query

    status = request.args.get("status")
    if status:
        upper_status = status.upper()
        if upper_status not in DEVICE_STATUSES:
            return jsonify({
                "error": "Invalid status filter.",
                "allowed": list(DEVICE_STATUSES),
            }), 400
        query = query.filter(Device.status == upper_status)

    device_type = request.args.get("device_type")
    if device_type:
        query = query.filter(Device.device_type == device_type)

    search = request.args.get("search", "").strip()
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Device.name.ilike(pattern),
                Device.ip_address.ilike(pattern),
                Device.location.ilike(pattern),
            )
        )

    devices = query.order_by(Device.id.asc()).all()
    return jsonify({
        "devices": [device.to_dict() for device in devices],
        "count": len(devices),
    }), 200


@devices_bp.get("/<int:device_id>")
def get_device(device_id: int):
    """Return a single device by ID."""
    device = db.session.get(Device, device_id)
    if device is None:
        return jsonify({"error": f"Device with id {device_id} not found."}), 404

    include_incidents = request.args.get("include_incidents", "false").lower() == "true"
    return jsonify({"device": device.to_dict(include_incidents=include_incidents)}), 200


@devices_bp.post("")
def create_device():
    """Register a new network device."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a valid JSON object."}), 400

    cleaned, errors = validate_device_payload(data, partial=False)
    if errors:
        return jsonify({"error": "Validation failed.", "details": errors}), 400

    # Check uniqueness explicitly for clean 409 conflict messages
    existing_name = Device.query.filter_by(name=cleaned["name"]).first()
    if existing_name:
        return jsonify({"error": f"Device name '{cleaned['name']}' already exists."}), 409

    existing_ip = Device.query.filter_by(ip_address=cleaned["ip_address"]).first()
    if existing_ip:
        return jsonify({"error": f"IP address '{cleaned['ip_address']}' is already registered."}), 409

    status = cleaned.get("status", "ONLINE")
    device = Device(
        name=cleaned["name"],
        ip_address=cleaned["ip_address"],
        device_type=cleaned["device_type"],
        location=cleaned["location"],
        status=status,
        simulated_latency_ms=None if status == "OFFLINE" else (85.0 if status == "WARNING" else 12.5),
        simulated_uptime_pct=94.0 if status == "OFFLINE" else (98.2 if status == "WARNING" else 99.95),
        last_checked=utc_now(),
    )

    try:
        db.session.add(device)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Device with duplicate name or IP address already exists."}), 409

    return jsonify({
        "message": "Device registered successfully.",
        "device": device.to_dict(),
    }), 201


@devices_bp.put("/<int:device_id>")
def update_device(device_id: int):
    """Update an existing network device."""
    device = db.session.get(Device, device_id)
    if device is None:
        return jsonify({"error": f"Device with id {device_id} not found."}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a valid JSON object."}), 400

    if not data:
        return jsonify({"error": "At least one updatable field must be provided."}), 400

    cleaned, errors = validate_device_payload(data, partial=True)
    if errors:
        return jsonify({"error": "Validation failed.", "details": errors}), 400

    if "name" in cleaned and cleaned["name"] != device.name:
        if Device.query.filter(Device.name == cleaned["name"], Device.id != device_id).first():
            return jsonify({"error": f"Device name '{cleaned['name']}' already exists."}), 409

    if "ip_address" in cleaned and cleaned["ip_address"] != device.ip_address:
        if Device.query.filter(Device.ip_address == cleaned["ip_address"], Device.id != device_id).first():
            return jsonify({"error": f"IP address '{cleaned['ip_address']}' is already registered."}), 409

    for field, value in cleaned.items():
        setattr(device, field, value)

    if "status" in cleaned:
        device.last_checked = utc_now()
        if cleaned["status"] == "OFFLINE":
            device.simulated_latency_ms = None
        elif device.simulated_latency_ms is None:
            device.simulated_latency_ms = 14.0 if cleaned["status"] == "ONLINE" else 95.0

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Device update conflicts with an existing device."}), 409

    return jsonify({
        "message": "Device updated successfully.",
        "device": device.to_dict(),
    }), 200


@devices_bp.delete("/<int:device_id>")
def delete_device(device_id: int):
    """Delete a device and cascade-remove its associated incidents."""
    device = db.session.get(Device, device_id)
    if device is None:
        return jsonify({"error": f"Device with id {device_id} not found."}), 404

    device_name = device.name
    db.session.delete(device)
    db.session.commit()

    return jsonify({
        "message": f"Device '{device_name}' and its associated incidents were deleted.",
        "deleted_id": device_id,
    }), 200
