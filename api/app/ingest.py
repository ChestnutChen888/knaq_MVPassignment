import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models import Alert, AlertTimeline, Device, RawMessage, Reading, User
from app.utils import (
    build_alert_title,
    build_dedupe_key,
    epoch_ms_to_utc_datetime,
    parse_date_optional,
    to_json_text,
)


VALID_MESSAGE_TYPES = {"reading", "alert", "recovery"}


def seed_users(db: Session) -> None:
    users = [
        User(
            id="u1",
            name="Alice Chen",
            email="alice@brookfield.example",
            role="Manager",
            company="Brookfield Properties",
            token="token-brookfield-manager",
        ),
        User(
            id="u2",
            name="Bob Smith",
            email="bob@brookfield.example",
            role="Technician",
            company="Brookfield Properties",
            token="token-brookfield-tech",
        ),
        User(
            id="u3",
            name="Lisa Wang",
            email="lisa@hines.example",
            role="Manager",
            company="Hines",
            token="token-hines-manager",
        ),
        User(
            id="u4",
            name="Mark Lee",
            email="mark@hines.example",
            role="Technician",
            company="Hines",
            token="token-hines-tech",
        ),
        User(
            id="u5",
            name="Priya Patel",
            email="priya@brookfield.example",
            role="Dispatcher",
            company="Brookfield Properties",
            token="token-brookfield-dispatcher",
        ),
    ]
    db.add_all(users)
    db.flush()


def load_devices(db: Session, path: Path) -> int:
    with path.open("r", encoding="utf-8") as file:
        devices = json.load(file)

    for item in devices:
        device = Device(
            device_id=item["device_id"],
            name=item["name"],
            type=item["type"],
            company=item["company"],
            location=item["location"],
            timezone=item["timezone"],
            installed_date=parse_date_optional(item.get("installed_date")),
            floor_count=item.get("floor_count"),
            reading_types_json=to_json_text(item.get("reading_types", [])),
            alert_thresholds_json=to_json_text(item.get("alert_thresholds", {})),
        )
        db.add(device)

    db.flush()
    return len(devices)


def ingest_sensor_messages(db: Session, path: Path) -> dict[str, int]:
    with path.open("r", encoding="utf-8") as file:
        messages = json.load(file)

    summary = {
        "total": 0,
        "inserted_raw": 0,
        "duplicates_skipped": 0,
        "invalid": 0,
        "readings_created": 0,
        "alerts_created": 0,
        "recoveries_matched": 0,
        "recoveries_unmatched": 0,
    }

    for message in messages:
        summary["total"] += 1
        ingest_one_message(db, message, summary)

    return summary


def ingest_one_message(db: Session, message: dict[str, Any], summary: dict[str, int]) -> None:
    dedupe_key = build_dedupe_key(message)
    existing = db.query(RawMessage).filter(RawMessage.dedupe_key == dedupe_key).first()

    if existing:
        summary["duplicates_skipped"] += 1
        return

    is_valid, invalid_reason = validate_base_message(db, message)
    timestamp_utc = None
    if isinstance(message.get("timestamp"), int):
        timestamp_utc = epoch_ms_to_utc_datetime(message["timestamp"])

    raw = RawMessage(
        dedupe_key=dedupe_key,
        device_id=message.get("device_id"),
        message_type=message.get("message_type"),
        timestamp_utc=timestamp_utc,
        payload_json=to_json_text(message),
        is_valid=is_valid,
        invalid_reason=invalid_reason,
    )
    db.add(raw)
    db.flush()
    summary["inserted_raw"] += 1

    if not is_valid:
        summary["invalid"] += 1
        return

    message_type = message["message_type"]
    if message_type == "reading":
        summary["readings_created"] += handle_reading_message(db, message, raw)
    elif message_type == "alert":
        handle_alert_message(db, message, raw)
        summary["alerts_created"] += 1
    elif message_type == "recovery":
        matched = handle_recovery_message(db, message, raw)
        key = "recoveries_matched" if matched else "recoveries_unmatched"
        summary[key] += 1


def validate_base_message(db: Session, message: dict[str, Any]) -> tuple[bool, str | None]:
    device_id = message.get("device_id")
    message_type = message.get("message_type")
    timestamp = message.get("timestamp")

    if not device_id:
        return False, "missing device_id"
    if not message_type:
        return False, "missing message_type"
    if message_type not in VALID_MESSAGE_TYPES:
        return False, f"invalid message_type: {message_type}"
    if not isinstance(timestamp, int):
        return False, "missing or invalid timestamp"

    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        return False, f"unknown device_id: {device_id}"

    if message_type == "reading" and not isinstance(message.get("inputs"), list):
        return False, "reading message missing inputs list"

    if message_type in {"alert", "recovery"}:
        if not message.get("alert_type"):
            return False, "missing alert_type"
        if not message.get("severity"):
            return False, "missing severity"

    return True, None


def handle_reading_message(db: Session, message: dict[str, Any], raw: RawMessage) -> int:
    device = db.query(Device).filter(Device.device_id == message["device_id"]).one()
    reading_types = json.loads(device.reading_types_json)
    thresholds = json.loads(device.alert_thresholds_json)

    count = 0
    for input_item in message["inputs"]:
        input_name = input_item.get("input_name")
        input_value = input_item.get("input_value")

        if not input_name:
            continue

        numeric_value = float(input_value) if isinstance(input_value, (int, float)) else None
        breached, threshold_value, direction = check_threshold(input_name, numeric_value, thresholds)

        reading = Reading(
            device_id=device.device_id,
            timestamp_utc=raw.timestamp_utc,
            input_name=input_name,
            input_value=numeric_value,
            is_expected_type=input_name in reading_types,
            breached_threshold=breached,
            threshold_value=threshold_value,
            threshold_direction=direction,
            source_raw_message_id=raw.id,
        )
        db.add(reading)
        count += 1

    db.flush()
    return count


def check_threshold(
    input_name: str,
    input_value: float | None,
    thresholds: dict[str, Any],
) -> tuple[bool, float | None, str | None]:
    if input_value is None:
        return False, None, None

    nested_config = thresholds.get(input_name)
    if isinstance(nested_config, dict):
        if "max" in nested_config and input_value > float(nested_config["max"]):
            return True, float(nested_config["max"]), "above"
        if "min" in nested_config and input_value < float(nested_config["min"]):
            return True, float(nested_config["min"]), "below"

    high_key = f"{input_name}_high"
    low_key = f"{input_name}_low"
    if high_key in thresholds and input_value > float(thresholds[high_key]):
        return True, float(thresholds[high_key]), "above"
    if low_key in thresholds and input_value < float(thresholds[low_key]):
        return True, float(thresholds[low_key]), "below"

    return False, None, None


def handle_alert_message(db: Session, message: dict[str, Any], raw: RawMessage) -> Alert:
    device = db.query(Device).filter(Device.device_id == message["device_id"]).one()
    alert_type = message["alert_type"]
    severity = message["severity"]

    alert = Alert(
        device_id=device.device_id,
        company=device.company,
        title=build_alert_title(severity=severity, alert_type=alert_type, device_name=device.name),
        alert_type=alert_type,
        severity=severity,
        triggered_at_utc=raw.timestamp_utc,
        reading_name=message.get("reading_name"),
        reading_value=message.get("reading_value"),
        threshold_value=message.get("threshold"),
        status="new",
        source_raw_message_id=raw.id,
    )
    db.add(alert)
    db.flush()

    db.add(
        AlertTimeline(
            alert_id=alert.id,
            timestamp_utc=raw.timestamp_utc,
            action="created",
            user_name="System",
            source_raw_message_id=raw.id,
            details_json=to_json_text(
                {
                    "source": "device_alert",
                    "message_type": "alert",
                }
            ),
            note=None,
        )
    )
    db.flush()
    return alert


def handle_recovery_message(db: Session, message: dict[str, Any], raw: RawMessage) -> bool:
    alert = (
        db.query(Alert)
        .filter(Alert.device_id == message["device_id"])
        .filter(Alert.alert_type == message["alert_type"])
        .filter(Alert.severity == message["severity"])
        .filter(Alert.recovered_at_utc.is_(None))
        .filter(Alert.triggered_at_utc <= raw.timestamp_utc)
        .order_by(Alert.triggered_at_utc.desc())
        .first()
    )

    if not alert:
        return False

    alert.recovered_at_utc = raw.timestamp_utc
    db.add(
        AlertTimeline(
            alert_id=alert.id,
            timestamp_utc=raw.timestamp_utc,
            action="recovered",
            user_name="System",
            source_raw_message_id=raw.id,
            details_json=to_json_text(
                {
                    "source": "device_recovery",
                    "message_type": "recovery",
                }
            ),
            note=None,
        )
    )
    db.flush()
    return True
