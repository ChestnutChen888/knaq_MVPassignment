import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any


def epoch_ms_to_utc_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).replace(tzinfo=None)


def build_dedupe_key(message: dict[str, Any]) -> str:
    normalized_message = normalize_for_dedupe(message)
    normalized = json.dumps(
        normalized_message,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_for_dedupe(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {
            key: normalize_for_dedupe(item)
            for key, item in value.items()
        }
        if isinstance(normalized.get("inputs"), list):
            normalized["inputs"] = sorted(
                normalized["inputs"],
                key=dedupe_input_sort_key,
            )
        return normalized

    if isinstance(value, list):
        return [normalize_for_dedupe(item) for item in value]

    return value


def dedupe_input_sort_key(value: Any) -> tuple[str, str]:
    if isinstance(value, dict):
        return (
            str(value.get("input_name", "")),
            canonical_json(value.get("input_value")),
        )
    return ("", canonical_json(value))


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def to_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def parse_date_optional(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def build_alert_title(severity: str, alert_type: str, device_name: str) -> str:
    readable = alert_type.replace("_", " ").title()
    return f"{severity.title()} {readable} on {device_name}"
