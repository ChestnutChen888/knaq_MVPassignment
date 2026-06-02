import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "dev.db"


class CheckRunner:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.failures: list[str] = []

    def pass_fail(self, name: str, passed: bool, detail: str = "") -> None:
        status = "PASS" if passed else "FAIL"
        suffix = f" - {detail}" if detail else ""
        print(f"[{status}] {name}{suffix}")
        if not passed:
            self.failures.append(f"{name}{suffix}")

    def scalar(self, query: str, params: tuple[Any, ...] = ()) -> Any:
        return self.connection.execute(query, params).fetchone()[0]

    def rows(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return self.connection.execute(query, params).fetchall()


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}. Run `python -m app.seed` first.")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    runner = CheckRunner(connection)

    print(f"Checking database: {DB_PATH}")
    print()

    check_table_counts(runner)
    check_message_types(runner)
    check_invalid_messages(runner)
    check_duplicates(runner)
    check_readings(runner)
    check_threshold_logic(runner)
    check_alert_sources(runner)
    check_timeline(runner)
    check_status_and_company(runner)
    check_orphans(runner)

    print()
    if runner.failures:
        print(f"FAILED: {len(runner.failures)} check(s) failed")
        for failure in runner.failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print("ALL CHECKS PASSED")


def check_table_counts(runner: CheckRunner) -> None:
    print("Table counts")
    expected = {
        "users": lambda count: count > 0,
        "devices": lambda count: count == 10,
        "raw_messages": lambda count: count > 0,
        "readings": lambda count: count > 0,
        "alerts": lambda count: count > 0,
        "alert_timeline": lambda count: count > 0,
    }

    for table_name, predicate in expected.items():
        count = runner.scalar(f"SELECT COUNT(*) FROM {table_name}")
        runner.pass_fail(f"{table_name} has expected count", predicate(count), f"count={count}")
    print()


def check_message_types(runner: CheckRunner) -> None:
    print("Raw message types")
    rows = runner.rows(
        """
        SELECT message_type, COUNT(*) AS count
        FROM raw_messages
        WHERE is_valid = 1
        GROUP BY message_type
        """
    )
    counts = {row["message_type"]: row["count"] for row in rows}
    print(f"  distribution={counts}")
    for message_type in ("reading", "alert", "recovery"):
        runner.pass_fail(
            f"raw_messages includes {message_type}",
            counts.get(message_type, 0) > 0,
            f"count={counts.get(message_type, 0)}",
        )
    print()


def check_invalid_messages(runner: CheckRunner) -> None:
    print("Malformed messages")
    invalid_count = runner.scalar("SELECT COUNT(*) FROM raw_messages WHERE is_valid = 0")
    missing_reason_count = runner.scalar(
        """
        SELECT COUNT(*)
        FROM raw_messages
        WHERE is_valid = 0
          AND (invalid_reason IS NULL OR invalid_reason = '')
        """
    )
    reasons = runner.rows(
        """
        SELECT invalid_reason, COUNT(*) AS count
        FROM raw_messages
        WHERE is_valid = 0
        GROUP BY invalid_reason
        ORDER BY count DESC
        """
    )
    print(f"  invalid_count={invalid_count}")
    print(f"  reasons={[(row['invalid_reason'], row['count']) for row in reasons]}")
    runner.pass_fail("invalid messages have reasons", missing_reason_count == 0)
    print()


def check_duplicates(runner: CheckRunner) -> None:
    print("Duplicate handling")
    duplicates = runner.rows(
        """
        SELECT dedupe_key, COUNT(*) AS count
        FROM raw_messages
        GROUP BY dedupe_key
        HAVING COUNT(*) > 1
        """
    )
    runner.pass_fail("no duplicate dedupe_key rows", len(duplicates) == 0, f"duplicates={len(duplicates)}")
    print()


def check_readings(runner: CheckRunner) -> None:
    print("Readings")
    input_counts = runner.rows(
        """
        SELECT input_name, COUNT(*) AS count
        FROM readings
        GROUP BY input_name
        ORDER BY count DESC
        """
    )
    print(f"  input_counts={[(row['input_name'], row['count']) for row in input_counts]}")
    runner.pass_fail("readings include input names", len(input_counts) > 0)
    unexpected = runner.scalar("SELECT COUNT(*) FROM readings WHERE is_expected_type = 0")
    print(f"  unexpected_input_type_count={unexpected}")
    print()


def check_threshold_logic(runner: CheckRunner) -> None:
    print("Threshold logic")
    rows = runner.rows(
        """
        SELECT
          r.id,
          r.device_id,
          r.input_name,
          r.input_value,
          r.breached_threshold,
          r.threshold_value,
          r.threshold_direction,
          d.alert_thresholds_json
        FROM readings r
        JOIN devices d ON r.device_id = d.device_id
        """
    )

    mismatches = []
    for row in rows:
        expected = expected_threshold_result(
            row["input_name"],
            row["input_value"],
            json.loads(row["alert_thresholds_json"]),
        )
        actual = (
            bool(row["breached_threshold"]),
            row["threshold_value"],
            row["threshold_direction"],
        )
        if not threshold_result_matches(actual, expected):
            mismatches.append((row["id"], actual, expected))

    breached_count = runner.scalar("SELECT COUNT(*) FROM readings WHERE breached_threshold = 1")
    runner.pass_fail(
        "all readings match device thresholds",
        len(mismatches) == 0,
        f"mismatches={len(mismatches)}, breached_count={breached_count}",
    )

    direction_rows = runner.rows(
        """
        SELECT input_name, threshold_direction, COUNT(*) AS count
        FROM readings
        WHERE breached_threshold = 1
        GROUP BY input_name, threshold_direction
        ORDER BY count DESC
        """
    )
    print(f"  breached_distribution={[(row['input_name'], row['threshold_direction'], row['count']) for row in direction_rows]}")
    print()


def expected_threshold_result(
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


def threshold_result_matches(
    actual: tuple[bool, float | None, str | None],
    expected: tuple[bool, float | None, str | None],
) -> bool:
    actual_breached, actual_value, actual_direction = actual
    expected_breached, expected_value, expected_direction = expected

    if actual_breached != expected_breached:
        return False
    if actual_direction != expected_direction:
        return False
    if actual_value is None or expected_value is None:
        return actual_value is expected_value
    return abs(actual_value - expected_value) < 0.000001


def check_alert_sources(runner: CheckRunner) -> None:
    print("Alert sources")
    bad_sources = runner.rows(
        """
        SELECT a.id AS alert_id, rm.message_type
        FROM alerts a
        JOIN raw_messages rm ON a.source_raw_message_id = rm.id
        WHERE rm.message_type != 'alert'
        """
    )
    missing_sources = runner.scalar("SELECT COUNT(*) FROM alerts WHERE source_raw_message_id IS NULL")
    runner.pass_fail("alerts have raw message source", missing_sources == 0, f"missing={missing_sources}")
    runner.pass_fail("alerts are created from raw alert messages", len(bad_sources) == 0, f"bad_sources={len(bad_sources)}")
    print()


def check_timeline(runner: CheckRunner) -> None:
    print("Timeline")
    missing_created = runner.rows(
        """
        SELECT a.id AS alert_id, COUNT(t.id) AS created_timeline_count
        FROM alerts a
        LEFT JOIN alert_timeline t
          ON a.id = t.alert_id
         AND t.action = 'created'
        GROUP BY a.id
        HAVING COUNT(t.id) != 1
        """
    )
    created_bad_source = runner.rows(
        """
        SELECT t.id AS timeline_id, rm.message_type
        FROM alert_timeline t
        JOIN raw_messages rm ON t.source_raw_message_id = rm.id
        WHERE t.action = 'created'
          AND rm.message_type != 'alert'
        """
    )
    recovered_bad_source = runner.rows(
        """
        SELECT t.id AS timeline_id, rm.message_type
        FROM alert_timeline t
        JOIN raw_messages rm ON t.source_raw_message_id = rm.id
        WHERE t.action = 'recovered'
          AND rm.message_type != 'recovery'
        """
    )
    recovered_missing_alert_time = runner.rows(
        """
        SELECT t.id AS timeline_id
        FROM alert_timeline t
        JOIN alerts a ON t.alert_id = a.id
        WHERE t.action = 'recovered'
          AND a.recovered_at_utc IS NULL
        """
    )
    recovered_time_mismatch = runner.rows(
        """
        SELECT t.id AS timeline_id
        FROM alert_timeline t
        JOIN alerts a ON t.alert_id = a.id
        WHERE t.action = 'recovered'
          AND t.timestamp_utc != a.recovered_at_utc
        """
    )
    null_created_at = runner.scalar("SELECT COUNT(*) FROM alert_timeline WHERE created_at IS NULL")
    null_source = runner.scalar("SELECT COUNT(*) FROM alert_timeline WHERE source_raw_message_id IS NULL")

    runner.pass_fail("each alert has exactly one created timeline", len(missing_created) == 0, f"bad_alerts={len(missing_created)}")
    runner.pass_fail("created timeline comes from alert raw messages", len(created_bad_source) == 0, f"bad_sources={len(created_bad_source)}")
    runner.pass_fail("recovered timeline comes from recovery raw messages", len(recovered_bad_source) == 0, f"bad_sources={len(recovered_bad_source)}")
    runner.pass_fail("recovered timeline has alert recovered_at", len(recovered_missing_alert_time) == 0, f"missing={len(recovered_missing_alert_time)}")
    runner.pass_fail("recovered timeline time matches alert recovered_at", len(recovered_time_mismatch) == 0, f"mismatches={len(recovered_time_mismatch)}")
    runner.pass_fail("timeline created_at populated", null_created_at == 0, f"null_created_at={null_created_at}")
    runner.pass_fail("timeline source_raw_message_id populated", null_source == 0, f"null_source={null_source}")
    print()


def check_status_and_company(runner: CheckRunner) -> None:
    print("Alert status and company")
    status_rows = runner.rows(
        """
        SELECT status, COUNT(*) AS count
        FROM alerts
        GROUP BY status
        """
    )
    statuses = {row["status"]: row["count"] for row in status_rows}
    print(f"  statuses={statuses}")
    runner.pass_fail("all initial alerts are new", set(statuses.keys()) == {"new"})

    company_mismatches = runner.rows(
        """
        SELECT a.id, a.company AS alert_company, d.company AS device_company
        FROM alerts a
        JOIN devices d ON a.device_id = d.device_id
        WHERE a.company != d.company
        """
    )
    runner.pass_fail("alert company matches device company", len(company_mismatches) == 0, f"mismatches={len(company_mismatches)}")
    print()


def check_orphans(runner: CheckRunner) -> None:
    print("Orphan checks")
    reading_orphans = runner.rows(
        """
        SELECT r.id
        FROM readings r
        LEFT JOIN devices d ON r.device_id = d.device_id
        WHERE d.device_id IS NULL
        """
    )
    alert_orphans = runner.rows(
        """
        SELECT a.id
        FROM alerts a
        LEFT JOIN devices d ON a.device_id = d.device_id
        WHERE d.device_id IS NULL
        """
    )
    timeline_orphans = runner.rows(
        """
        SELECT t.id
        FROM alert_timeline t
        LEFT JOIN alerts a ON t.alert_id = a.id
        WHERE a.id IS NULL
        """
    )
    runner.pass_fail("readings have devices", len(reading_orphans) == 0, f"orphans={len(reading_orphans)}")
    runner.pass_fail("alerts have devices", len(alert_orphans) == 0, f"orphans={len(alert_orphans)}")
    runner.pass_fail("timeline entries have alerts", len(timeline_orphans) == 0, f"orphans={len(timeline_orphans)}")
    print()


if __name__ == "__main__":
    main()
