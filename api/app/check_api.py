from fastapi.testclient import TestClient

from app.main import app


TOKEN = "token-brookfield-manager"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


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

    alerts_response = client.get("/alerts", headers=HEADERS)
    check("GET /alerts returns 200", alerts_response.status_code == 200, f"status={alerts_response.status_code}")
    alerts = alerts_response.json()
    check("GET /alerts has items", len(alerts["items"]) > 0, f"items={len(alerts['items'])}")
    check("GET /alerts summary includes new", "new" in alerts["summary"], f"summary={alerts['summary']}")

    first_alert = alerts["items"][0]
    detail_response = client.get(f"/alerts/{first_alert['id']}", headers=HEADERS)
    check("GET /alerts/{id} returns 200", detail_response.status_code == 200, f"status={detail_response.status_code}")
    detail = detail_response.json()
    check("alert detail has timeline", len(detail["timeline"]) > 0, f"timeline={len(detail['timeline'])}")

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
        check("reading timestamp is local ISO", "T" in sample["timestamp"] and sample["timestamp"][-6:-5] in ["+", "-"])

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

    assign_resolved = client.post(
        f"/alerts/{first_alert['id']}/assign",
        headers=HEADERS,
        json={"assignee_id": "u2"},
    )
    check("assign resolved alert returns 409", assign_resolved.status_code == 409, f"status={assign_resolved.status_code}")

    hines_device = client.get("/devices/ELV-003", headers=HEADERS)
    check("cross-company device returns 404", hines_device.status_code == 404, f"status={hines_device.status_code}")

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
