from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api_utils import get_company_alert_or_404, timeline_to_response, utc_iso
from app.auth import get_current_user
from app.database import get_db
from app.models import Alert, AlertTimeline, Device, User
from app.schemas import (
    AddNoteRequest,
    AlertDetailResponse,
    AlertListResponse,
    AssignAlertRequest,
    ResolveAlertRequest,
)
from app.services.alert_service import (
    acknowledge_alert,
    add_note,
    assign_alert,
    dismiss_alert,
    reopen_alert,
    resolve_alert,
)


router = APIRouter(prefix="/alerts", tags=["alerts"])


def split_multi(values: list[str] | None) -> list[str]:
    if not values:
        return []
    result: list[str] = []
    for value in values:
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return result


@router.get("", response_model=AlertListResponse)
def list_alerts(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    severity: Annotated[list[str] | None, Query()] = None,
    status: Annotated[list[str] | None, Query()] = None,
    device_id: str | None = None,
    assigned_to: str | None = None,
    q: str | None = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AlertListResponse:
    query = db.query(Alert).join(Device, Alert.device_id == Device.device_id).filter(
        Alert.company == current_user.company
    )

    severities = split_multi(severity)
    statuses = split_multi(status)
    if severities:
        query = query.filter(Alert.severity.in_(severities))
    if statuses:
        query = query.filter(Alert.status.in_(statuses))
    if device_id:
        query = query.filter(Alert.device_id == device_id)
    if assigned_to:
        query = query.filter(Alert.assigned_to_user_id == assigned_to)
    if from_:
        query = query.filter(Alert.triggered_at_utc >= from_.replace(tzinfo=None))
    if to:
        query = query.filter(Alert.triggered_at_utc <= to.replace(tzinfo=None))
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Alert.title.ilike(pattern),
                Alert.alert_type.ilike(pattern),
                Alert.device_id.ilike(pattern),
                Device.name.ilike(pattern),
                Device.location.ilike(pattern),
            )
        )

    total = query.count()
    alerts = query.order_by(Alert.triggered_at_utc.desc()).offset(offset).limit(limit).all()
    summary = build_company_summary(db, current_user.company)

    return AlertListResponse(
        items=[alert_to_list_item(db, alert) for alert in alerts],
        total=total,
        summary=summary,
    )


@router.get("/{alert_id}", response_model=AlertDetailResponse)
def get_alert(
    alert_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AlertDetailResponse:
    alert = get_company_alert_or_404(db, alert_id, current_user)
    return alert_to_detail(db, alert)


@router.post("/{alert_id}/acknowledge", response_model=AlertDetailResponse)
def acknowledge_alert_endpoint(
    alert_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AlertDetailResponse:
    alert = acknowledge_alert(db, alert_id, current_user)
    return alert_to_detail(db, alert)


@router.post("/{alert_id}/assign", response_model=AlertDetailResponse)
def assign_alert_endpoint(
    alert_id: int,
    payload: AssignAlertRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AlertDetailResponse:
    alert = assign_alert(db, alert_id, payload, current_user)
    return alert_to_detail(db, alert)


@router.post("/{alert_id}/resolve", response_model=AlertDetailResponse)
def resolve_alert_endpoint(
    alert_id: int,
    payload: ResolveAlertRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AlertDetailResponse:
    alert = resolve_alert(db, alert_id, payload, current_user)
    return alert_to_detail(db, alert)


@router.post("/{alert_id}/dismiss", response_model=AlertDetailResponse)
def dismiss_alert_endpoint(
    alert_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AlertDetailResponse:
    alert = dismiss_alert(db, alert_id, current_user)
    return alert_to_detail(db, alert)


@router.post("/{alert_id}/reopen", response_model=AlertDetailResponse)
def reopen_alert_endpoint(
    alert_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AlertDetailResponse:
    alert = reopen_alert(db, alert_id, current_user)
    return alert_to_detail(db, alert)


@router.post("/{alert_id}/notes", response_model=AlertDetailResponse)
def add_note_endpoint(
    alert_id: int,
    payload: AddNoteRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AlertDetailResponse:
    alert = add_note(db, alert_id, payload.note, current_user)
    return alert_to_detail(db, alert)


def build_company_summary(db: Session, company: str) -> dict[str, int]:
    summary = {"new": 0, "acknowledged": 0, "resolved": 0, "dismissed": 0}
    rows = (
        db.query(Alert.status, Alert.id)
        .filter(Alert.company == company)
        .all()
    )
    for row in rows:
        summary[row.status] = summary.get(row.status, 0) + 1
    return summary


def alert_to_list_item(db: Session, alert: Alert) -> dict:
    device = db.query(Device).filter(Device.device_id == alert.device_id).one()
    assignee = db.query(User).filter(User.id == alert.assigned_to_user_id).first()
    return {
        "id": alert.id,
        "title": alert.title,
        "device_id": alert.device_id,
        "device_name": device.name,
        "device_location": device.location,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "status": alert.status,
        "assigned_to": user_to_response(assignee) if assignee else None,
        "triggered_at": utc_iso(alert.triggered_at_utc),
        "recovered_at": utc_iso(alert.recovered_at_utc),
        "reading_name": alert.reading_name,
        "reading_value": alert.reading_value,
        "threshold_value": alert.threshold_value,
    }


def alert_to_detail(db: Session, alert: Alert) -> dict:
    base = alert_to_list_item(db, alert)
    device = db.query(Device).filter(Device.device_id == alert.device_id).one()
    timeline = (
        db.query(AlertTimeline)
        .filter(AlertTimeline.alert_id == alert.id)
        .order_by(AlertTimeline.timestamp_utc.asc(), AlertTimeline.id.asc())
        .all()
    )
    base.update(
        {
            "device": {
                "device_id": device.device_id,
                "name": device.name,
                "type": device.type,
                "company": device.company,
                "location": device.location,
                "timezone": device.timezone,
                "installed_date": device.installed_date.isoformat() if device.installed_date else None,
                "floor_count": device.floor_count,
            },
            "acknowledged_at": utc_iso(alert.acknowledged_at_utc),
            "resolved_at": utc_iso(alert.resolved_at_utc),
            "resolution": build_resolution(alert),
            "timeline": [timeline_to_response(entry) for entry in timeline],
        }
    )
    return base


def build_resolution(alert: Alert) -> dict | None:
    if alert.resolution_type is None:
        return None
    return {
        "type": alert.resolution_type,
        "root_cause": alert.resolution_root_cause,
        "action_taken": alert.resolution_action_taken,
        "preventive_measures": alert.resolution_preventive_measures,
        "time_spent_minutes": alert.resolution_time_spent_minutes,
    }


def user_to_response(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "company": user.company,
    }
