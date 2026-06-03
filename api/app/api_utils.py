import json
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Alert, AlertTimeline, Device, User


UTC = ZoneInfo("UTC")


def utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        utc_value = value.replace(tzinfo=UTC)
    else:
        utc_value = value.astimezone(UTC)
    return utc_value.isoformat().replace("+00:00", "Z")


def local_to_utc_naive(value: str, timezone_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid datetime: {value}",
        ) from exc

    tz = ZoneInfo(timezone_name)
    if parsed.tzinfo is None:
        local = parsed.replace(tzinfo=tz)
    else:
        local = parsed.astimezone(tz)
    return local.astimezone(UTC).replace(tzinfo=None)


def utc_naive_to_local_iso(value: datetime, timezone_name: str) -> str:
    if value.tzinfo is None:
        utc_value = value.replace(tzinfo=UTC)
    else:
        utc_value = value.astimezone(UTC)
    return utc_value.astimezone(ZoneInfo(timezone_name)).isoformat()


def json_text_to_dict(value: str | None) -> dict:
    if not value:
        return {}
    parsed = json.loads(value)
    return parsed if isinstance(parsed, dict) else {}


def json_text_to_list(value: str | None) -> list:
    if not value:
        return []
    parsed = json.loads(value)
    return parsed if isinstance(parsed, list) else []


def parse_details(value: str | None) -> dict | None:
    if not value:
        return None
    parsed = json.loads(value)
    return parsed if isinstance(parsed, dict) else None


def get_company_alert_or_404(db: Session, alert_id: int, current_user: User) -> Alert:
    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id)
        .filter(Alert.company == current_user.company)
        .first()
    )
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    return alert


def get_company_device_or_404(db: Session, device_id: str, current_user: User) -> Device:
    device = (
        db.query(Device)
        .filter(Device.device_id == device_id)
        .filter(Device.company == current_user.company)
        .first()
    )
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    return device


def timeline_to_response(entry: AlertTimeline) -> dict:
    return {
        "id": entry.id,
        "timestamp": utc_iso(entry.timestamp_utc),
        "action": entry.action,
        "user_name": entry.user_name,
        "source_raw_message_id": entry.source_raw_message_id,
        "details": parse_details(entry.details_json),
        "note": entry.note,
        "created_at": utc_iso(entry.created_at),
    }
