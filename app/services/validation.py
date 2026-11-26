"""Input validation helpers for REST API payloads."""

import ipaddress
from typing import Any

from app.models import (
    DEVICE_STATUSES,
    DEVICE_TYPES,
    INCIDENT_PRIORITIES,
    INCIDENT_STATUSES,
)


def validate_ip_address(value: Any) -> str | None:
    """Return normalized IPv4/IPv6 string if valid, else None."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return str(ipaddress.ip_address(stripped))
    except ValueError:
        return None


def validate_non_empty_str(value: Any, field_name: str, max_length: int) -> tuple[str | None, str | None]:
    """Validate that a value is a non-empty string within max_length."""
    if not isinstance(value, str) or not value.strip():
        return None, f"'{field_name}' must be a non-empty string."
    cleaned = value.strip()
    if len(cleaned) > max_length:
        return None, f"'{field_name}' must not exceed {max_length} characters."
    return cleaned, None


def validate_device_payload(data: dict, partial: bool = False) -> tuple[dict, dict]:
    """Validate device creation or update JSON payload.

    Returns:
        (cleaned_data, errors_dict)
    """
    errors: dict[str, str] = {}
    cleaned: dict[str, Any] = {}

    if not partial or "name" in data:
        name, err = validate_non_empty_str(data.get("name"), "name", 100)
        if err:
            errors["name"] = err
        else:
            cleaned["name"] = name

    if not partial or "ip_address" in data:
        ip_val = validate_ip_address(data.get("ip_address"))
        if ip_val is None:
            errors["ip_address"] = "'ip_address' must be a valid IPv4 or IPv6 address."
        else:
            cleaned["ip_address"] = ip_val

    if not partial or "device_type" in data:
        dtype, err = validate_non_empty_str(data.get("device_type"), "device_type", 50)
        if err:
            errors["device_type"] = err
        elif dtype not in DEVICE_TYPES:
            errors["device_type"] = (
                f"'device_type' must be one of: {', '.join(DEVICE_TYPES)}."
            )
        else:
            cleaned["device_type"] = dtype

    if not partial or "location" in data:
        loc, err = validate_non_empty_str(data.get("location"), "location", 120)
        if err:
            errors["location"] = err
        else:
            cleaned["location"] = loc

    if "status" in data:
        status = data.get("status")
        if not isinstance(status, str) or status.upper() not in DEVICE_STATUSES:
            errors["status"] = (
                f"'status' must be one of: {', '.join(DEVICE_STATUSES)}."
            )
        else:
            cleaned["status"] = status.upper()

    return cleaned, errors


def validate_incident_payload(data: dict, partial: bool = False) -> tuple[dict, dict]:
    """Validate incident creation or update JSON payload.

    Returns:
        (cleaned_data, errors_dict)
    """
    errors: dict[str, str] = {}
    cleaned: dict[str, Any] = {}

    if not partial or "device_id" in data:
        raw_device_id = data.get("device_id")
        if isinstance(raw_device_id, bool) or not isinstance(raw_device_id, int) or raw_device_id <= 0:
            errors["device_id"] = "'device_id' must be a positive integer."
        else:
            cleaned["device_id"] = raw_device_id

    if not partial or "title" in data:
        title, err = validate_non_empty_str(data.get("title"), "title", 150)
        if err:
            errors["title"] = err
        else:
            cleaned["title"] = title

    if "description" in data:
        desc = data.get("description")
        if desc is None:
            cleaned["description"] = ""
        elif not isinstance(desc, str):
            errors["description"] = "'description' must be a string."
        else:
            cleaned["description"] = desc.strip()

    if "priority" in data:
        priority = data.get("priority")
        if not isinstance(priority, str) or priority.upper() not in INCIDENT_PRIORITIES:
            errors["priority"] = (
                f"'priority' must be one of: {', '.join(INCIDENT_PRIORITIES)}."
            )
        else:
            cleaned["priority"] = priority.upper()

    if "status" in data:
        status = data.get("status")
        if not isinstance(status, str) or status.upper() not in INCIDENT_STATUSES:
            errors["status"] = (
                f"'status' must be one of: {', '.join(INCIDENT_STATUSES)}."
            )
        else:
            cleaned["status"] = status.upper()

    return cleaned, errors
