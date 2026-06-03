from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


TOKEN = "token-brookfield-manager"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
OTHER_HEADERS = {"Authorization": "Bearer token-hines-manager"}
EXPECTED_STATUS_KEYS = {"new", "acknowledged", "resolved", "dismissed"}


"""
Smoke test for the API layer.

This script exercises mutations and therefore changes dev.db. For repeatable
results, run `python -m app.seed` before `python -m app.check_api`.
"""


def main() -> None:
    client = TestClient(app)
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        suffix = f" - {detail}" if detail else ""
        print(f"[{status}] {name}{suffix}")
        if not condition:
            failures.append(f"{name}{suffix}")

    health = client.get("/health")
    check("health endpoint", health.status_code == 200, f"status={health.status_code}")

    unauthorized = client.get("/alerts")
    check("missing token returns 401", unauthorized.status_code == 401, f"status={unauthorized.status_code}")

    invalid_token = client.get("/alerts", headers={"Authorization": "Bearer invalid-token"})
    check("invalid token returns 401", invalid_token.status_code == 401, f"status={invalid_token.status_code}")

    alerts_response = client.get("/alerts", headers=HEADERS)
    check("GET /alerts returns 200", alerts_response.status_code == 200, f"status={alerts_response.status_code}")
    alerts = alerts_response.json()
    check("GET /alerts has items", len(alerts["items"]) > 0, f"items={len(alerts['items'])}")
    check(
        "summary has expected status keys",
        EXPECTED_STATUS_KEYS.issubset(alerts["summary"].keys()),
        f"summary={alerts['summary']}",
    )

    paged_response = client.get(
        "/alerts",
        headers=HEADERS,
        params={"page": 1, "page_size": 5},
    )
    check("GET /alerts supports page pagination", paged_response.status_code == 200, f"status={paged_response.status_code}")
    paged = paged_response.json()
    check(
        "paginated alerts respect page_size",
        len(paged["items"]) <= 5 and paged["page"] == 1 and paged["page_size"] == 5,
        f"items={len(paged['items'])}, page={paged.get('page')}, page_size={paged.get('page_size')}",
    )
    check(
        "paginated alerts keep total count",
        paged["total"] == alerts["total"],
        f"page_total={paged['total']}, total={alerts['total']}",
    )
    severity_sorted_response = client.get(
        "/alerts",
        headers=HEADERS,
        params={"page": 1, "page_size": 5, "sort_by": "severity", "sort_order": "desc"},
    )
    check(
        "GET /alerts supports severity sorting",
        severity_sorted_response.status_code == 200,
        f"status={severity_sorted_response.status_code}",
    )
    severity_sorted = severity_sorted_response.json()["items"]
    if severity_sorted:
        check(
            "severity sorting puts critical alerts first",
            severity_sorted[0]["severity"] == "critical",
            f"first_severity={severity_sorted[0]['severity']}",
        )

    new_alert = next((item for item in alerts["items"] if item["status"] == "new"), None)
    check("has a new alert for workflow test", new_alert is not None)
    if new_alert is None:
        raise SystemExit(1)

    first_alert = new_alert
    dismiss_candidate = next(
        (
            item
            for item in alerts["items"]
            if item["status"] == "new" and item["id"] != first_alert["id"]
        ),
        None,
    )
    check("has a second new alert for dismiss/reopen test", dismiss_candidate is not None)

    if dismiss_candidate is not None:
        reopen_new = client.post(f"/alerts/{dismiss_candidate['id']}/reopen", headers=HEADERS)
        check("reopen new alert returns 409", reopen_new.status_code == 409, f"status={reopen_new.status_code}")

        dismiss_new = client.post(f"/alerts/{dismiss_candidate['id']}/dismiss", headers=HEADERS)
        check("dismiss new alert returns 200", dismiss_new.status_code == 200, f"status={dismiss_new.status_code}")
        dismissed = dismiss_new.json()
        check("dismiss changes status", dismissed["status"] == "dismissed", f"status={dismissed['status']}")
        check(
            "dismiss appends dismissed timeline",
            dismissed["timeline"][-1]["action"] == "dismissed",
            f"last_action={dismissed['timeline'][-1]['action']}",
        )

        reopen_dismissed = client.post(f"/alerts/{dismiss_candidate['id']}/reopen", headers=HEADERS)
        check(
            "reopen dismissed alert returns 200",
            reopen_dismissed.status_code == 200,
            f"status={reopen_dismissed.status_code}",
        )
        reopened = reopen_dismissed.json()
        check("reopen changes status to acknowledged", reopened["status"] == "acknowledged", f"status={reopened['status']}")
        check(
            "reopen appends reopened timeline",
            reopened["timeline"][-1]["action"] == "reopened",
            f"last_action={reopened['timeline'][-1]['action']}",
        )

        dismiss_acknowledged = client.post(f"/alerts/{dismiss_candidate['id']}/dismiss", headers=HEADERS)
        check(
            "dismiss acknowledged alert returns 200",
            dismiss_acknowledged.status_code == 200,
            f"status={dismiss_acknowledged.status_code}",
        )

    detail_response = client.get(f"/alerts/{first_alert['id']}", headers=HEADERS)
    check("GET /alerts/{id} returns 200", detail_response.status_code == 200, f"status={detail_response.status_code}")
    detail = detail_response.json()
    check("alert detail has timeline", len(detail["timeline"]) > 0, f"timeline={len(detail['timeline'])}")

    resolve_new = client.post(
        f"/alerts/{first_alert['id']}/resolve",
        headers=HEADERS,
        json={
            "resolution_type": "fixed",
            "root_cause": "Should not be allowed before acknowledge.",
            "action_taken": "Attempted direct resolve.",
        },
    )
    check("resolve new alert returns 409", resolve_new.status_code == 409, f"status={resolve_new.status_code}")

    bad_assign = client.post(
        f"/alerts/{first_alert['id']}/assign",
        headers=HEADERS,
        json={"assignee_id": "u3"},
    )
    check("assign cross-company user returns 404", bad_assign.status_code == 404, f"status={bad_assign.status_code}")

    devices_response = client.get("/devices", headers=HEADERS)
    check("GET /devices returns 200", devices_response.status_code == 200, f"status={devices_response.status_code}")
    devices = devices_response.json()
    check("devices are company scoped", all(device["company"] == "Brookfield Properties" for device in devices))

    users_response = client.get("/users", headers=HEADERS)
    check("GET /users returns 200", users_response.status_code == 200, f"status={users_response.status_code}")
    users = users_response.json()
    check("users are company scoped", all(user["company"] == "Brookfield Properties" for user in users))

    readings_response = client.get(
        "/devices/ELV-001/readings",
        headers=HEADERS,
        params={
            "start": "2026-02-10T00:00:00",
            "end": "2026-02-13T23:59:59",
            "breached_only": "true",
        },
    )
    check(
        "GET /devices/{id}/readings breached_only returns 200",
        readings_response.status_code == 200,
        f"status={readings_response.status_code}",
    )
    readings = readings_response.json()
    check(
        "breached_only readings are all breached",
        all(item["breached_threshold"] is True for item in readings["items"]),
        f"items={len(readings['items'])}",
    )
    if readings["items"]:
        sample = readings["items"][0]
        parsed_timestamp = datetime.fromisoformat(sample["timestamp"])
        check("reading timestamp has timezone", parsed_timestamp.tzinfo is not None)

    acknowledge_response = client.post(f"/alerts/{first_alert['id']}/acknowledge", headers=HEADERS)
    check(
        "POST /alerts/{id}/acknowledge returns 200",
        acknowledge_response.status_code == 200,
        f"status={acknowledge_response.status_code}",
    )
    acknowledged = acknowledge_response.json()
    check("acknowledge changes status", acknowledged["status"] == "acknowledged", f"status={acknowledged['status']}")

    repeat_acknowledge = client.post(f"/alerts/{first_alert['id']}/acknowledge", headers=HEADERS)
    check(
        "repeat acknowledge returns 409",
        repeat_acknowledge.status_code == 409,
        f"status={repeat_acknowledge.status_code}",
    )

    assign_response = client.post(
        f"/alerts/{first_alert['id']}/assign",
        headers=HEADERS,
        json={"assignee_id": "u2", "note": "Smoke test assignment."},
    )
    check("POST /alerts/{id}/assign returns 200", assign_response.status_code == 200, f"status={assign_response.status_code}")
    assigned = assign_response.json()
    check("assign sets assignee", assigned["assigned_to"]["id"] == "u2")

    resolve_response = client.post(
        f"/alerts/{first_alert['id']}/resolve",
        headers=HEADERS,
        json={
            "resolution_type": "fixed",
            "root_cause": "Smoke test root cause.",
            "action_taken": "Smoke test action.",
            "preventive_measures": "Smoke test prevention.",
            "time_spent_minutes": 15,
        },
    )
    check("POST /alerts/{id}/resolve returns 200", resolve_response.status_code == 200, f"status={resolve_response.status_code}")
    resolved = resolve_response.json()
    check("resolve changes status", resolved["status"] == "resolved", f"status={resolved['status']}")

    note_response = client.post(
        f"/alerts/{first_alert['id']}/notes",
        headers=HEADERS,
        json={"note": "Smoke test note after resolution."},
    )
    check("POST /alerts/{id}/notes returns 200", note_response.status_code == 200, f"status={note_response.status_code}")
    noted = note_response.json()
    note_entries = [
        entry
        for entry in noted["timeline"]
        if entry["action"] == "note_added" and entry["note"] == "Smoke test note after resolution."
    ]
    check("add note appends note_added timeline", len(note_entries) == 1, f"matches={len(note_entries)}")
    timeline_actions = [entry["action"] for entry in noted["timeline"]]
    expected_workflow_actions = ["created", "acknowledged", "assigned", "resolved", "note_added"]
    check(
        "workflow timeline contains required actions",
        all(action in timeline_actions for action in expected_workflow_actions),
        f"actions={timeline_actions}",
    )
    action_positions = [timeline_actions.index(action) for action in expected_workflow_actions]
    check(
        "workflow timeline actions are ordered",
        action_positions == sorted(action_positions),
        f"positions={action_positions}",
    )
    timeline_timestamps = [datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")) for entry in noted["timeline"]]
    check(
        "timeline timestamps are sorted",
        timeline_timestamps == sorted(timeline_timestamps),
    )

    assign_resolved = client.post(
        f"/alerts/{first_alert['id']}/assign",
        headers=HEADERS,
        json={"assignee_id": "u2"},
    )
    check("assign resolved alert returns 409", assign_resolved.status_code == 409, f"status={assign_resolved.status_code}")

    dismiss_resolved = client.post(f"/alerts/{first_alert['id']}/dismiss", headers=HEADERS)
    check("dismiss resolved alert returns 409", dismiss_resolved.status_code == 409, f"status={dismiss_resolved.status_code}")

    reopen_resolved = client.post(f"/alerts/{first_alert['id']}/reopen", headers=HEADERS)
    check("reopen resolved alert returns 200", reopen_resolved.status_code == 200, f"status={reopen_resolved.status_code}")
    reopened_resolved = reopen_resolved.json()
    check(
        "reopen resolved alert changes status to acknowledged",
        reopened_resolved["status"] == "acknowledged",
        f"status={reopened_resolved['status']}",
    )
    check(
        "reopen clears active resolution",
        reopened_resolved["resolution"] is None and reopened_resolved["resolved_at"] is None,
    )

    hines_device = client.get("/devices/ELV-003", headers=HEADERS)
    check("cross-company device returns 404", hines_device.status_code == 404, f"status={hines_device.status_code}")

    other_alerts_response = client.get("/alerts", headers=OTHER_HEADERS)
    check(
        "other company GET /alerts returns 200",
        other_alerts_response.status_code == 200,
        f"status={other_alerts_response.status_code}",
    )
    other_alerts = other_alerts_response.json()["items"]
    if other_alerts:
        cross_alert = client.get(f"/alerts/{other_alerts[0]['id']}", headers=HEADERS)
        check("cross-company alert detail returns 404", cross_alert.status_code == 404, f"status={cross_alert.status_code}")

    if failures:
        print()
        print(f"FAILED: {len(failures)} API check(s) failed")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print()
    print("ALL API CHECKS PASSED")


if __name__ == "__main__":
    main()
