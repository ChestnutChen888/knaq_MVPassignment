from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.ingest import ingest_sensor_messages, load_devices, seed_users
from app.main import app


BROOKFIELD_HEADERS = {"Authorization": "Bearer token-brookfield-manager"}
HINES_HEADERS = {"Authorization": "Bearer token-hines-manager"}
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)
    db = testing_session_local()
    try:
        seed_users(db)
        load_devices(db, DATA_DIR / "devices.json")
        ingest_sensor_messages(db, DATA_DIR / "sensor_messages.json")
        db.commit()
    finally:
        db.close()

    def override_get_db() -> Generator[Session, None, None]:
        test_db = testing_session_local()
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_alert_workflow_and_company_scope(client: TestClient) -> None:
    assert client.get("/alerts").status_code == 401
    assert client.get("/alerts", headers={"Authorization": "Bearer bad"}).status_code == 401

    alerts_response = client.get("/alerts", headers=BROOKFIELD_HEADERS)
    assert alerts_response.status_code == 200
    alerts = alerts_response.json()["items"]
    assert alerts

    hines_alerts = client.get("/alerts", headers=HINES_HEADERS).json()["items"]
    assert hines_alerts
    cross_company_response = client.get(
        f"/alerts/{hines_alerts[0]['id']}",
        headers=BROOKFIELD_HEADERS,
    )
    assert cross_company_response.status_code == 404

    new_alerts = [item for item in alerts if item["status"] == "new"]
    assert len(new_alerts) >= 2
    dismiss_alert_id = new_alerts[0]["id"]
    resolve_alert_id = new_alerts[1]["id"]

    reopen_new_response = client.post(
        f"/alerts/{dismiss_alert_id}/reopen",
        headers=BROOKFIELD_HEADERS,
    )
    assert reopen_new_response.status_code == 409

    dismiss_response = client.post(
        f"/alerts/{dismiss_alert_id}/dismiss",
        headers=BROOKFIELD_HEADERS,
    )
    assert dismiss_response.status_code == 200
    dismissed = dismiss_response.json()
    assert dismissed["status"] == "dismissed"
    assert dismissed["timeline"][-1]["action"] == "dismissed"

    assign_dismissed_response = client.post(
        f"/alerts/{dismiss_alert_id}/assign",
        headers=BROOKFIELD_HEADERS,
        json={"assignee_id": "u2"},
    )
    assert assign_dismissed_response.status_code == 409

    reopen_dismissed_response = client.post(
        f"/alerts/{dismiss_alert_id}/reopen",
        headers=BROOKFIELD_HEADERS,
    )
    assert reopen_dismissed_response.status_code == 200
    reopened = reopen_dismissed_response.json()
    assert reopened["status"] == "acknowledged"
    assert reopened["timeline"][-1]["action"] == "reopened"

    acknowledge_response = client.post(
        f"/alerts/{resolve_alert_id}/acknowledge",
        headers=BROOKFIELD_HEADERS,
    )
    assert acknowledge_response.status_code == 200
    assert acknowledge_response.json()["status"] == "acknowledged"

    resolve_response = client.post(
        f"/alerts/{resolve_alert_id}/resolve",
        headers=BROOKFIELD_HEADERS,
        json={
            "resolution_type": "fixed",
            "root_cause": "Pytest verified root cause.",
            "action_taken": "Pytest verified action.",
            "preventive_measures": "Monitor the next maintenance window.",
            "time_spent_minutes": 20,
        },
    )
    assert resolve_response.status_code == 200
    resolved = resolve_response.json()
    assert resolved["status"] == "resolved"
    assert resolved["resolution"]["type"] == "fixed"

    dismiss_resolved_response = client.post(
        f"/alerts/{resolve_alert_id}/dismiss",
        headers=BROOKFIELD_HEADERS,
    )
    assert dismiss_resolved_response.status_code == 409

    reopen_resolved_response = client.post(
        f"/alerts/{resolve_alert_id}/reopen",
        headers=BROOKFIELD_HEADERS,
    )
    assert reopen_resolved_response.status_code == 200
    reopened_resolved = reopen_resolved_response.json()
    assert reopened_resolved["status"] == "acknowledged"
    assert reopened_resolved["resolution"] is None
    assert reopened_resolved["resolved_at"] is None


def test_breached_readings_are_exposed(client: TestClient) -> None:
    response = client.get(
        "/devices/ELV-001/readings",
        headers=BROOKFIELD_HEADERS,
        params={
            "start": "2026-02-10T00:00:00",
            "end": "2026-02-13T23:59:59",
            "breached_only": "true",
        },
    )

    assert response.status_code == 200
    readings = response.json()["items"]
    assert readings
    assert all(item["breached_threshold"] is True for item in readings)
    assert all(item["threshold_value"] is not None for item in readings)
    assert all(item["threshold_direction"] in {"above", "below"} for item in readings)
