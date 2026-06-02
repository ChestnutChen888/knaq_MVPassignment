import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any


def epoch_ms_to_utc_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).replace(tzinfo=None)


def build_dedupe_key(message: dict[str, Any]) -> str:
    normalized = json.dumps(
        message,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def to_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def parse_date_optional(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def build_alert_title(severity: str, alert_type: str, device_name: str) -> str:
    readable = alert_type.replace("_", " ").title()
    return f"{severity.title()} {readable} on {device_name}"
