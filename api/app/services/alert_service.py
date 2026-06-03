from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api_utils import get_company_alert_or_404
from app.models import Alert, AlertTimeline, User
from app.schemas import AssignAlertRequest, ResolveAlertRequest
from app.utils import to_json_text


TERMINAL_STATUSES = {"resolved", "dismissed"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def acknowledge_alert(db: Session, alert_id: int, current_user: User) -> Alert:
    alert = get_company_alert_or_404(db, alert_id, current_user)
    if alert.status != "new":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only new alerts can be acknowledged.",
        )

    now = utc_now()
    alert.status = "acknowledged"
    alert.acknowledged_at_utc = now
    append_timeline(
        db=db,
        alert=alert,
        timestamp=now,
        action="acknowledged",
        user_name=current_user.name,
        details={"from_status": "new", "to_status": "acknowledged"},
    )
    db.commit()
    db.refresh(alert)
    return alert


def assign_alert(
    db: Session,
    alert_id: int,
    payload: AssignAlertRequest,
    current_user: User,
) -> Alert:
    alert = get_company_alert_or_404(db, alert_id, current_user)
    if alert.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resolved or dismissed alerts cannot be assigned.",
        )

    assignee = (
        db.query(User)
        .filter(User.id == payload.assignee_id)
        .filter(User.company == current_user.company)
        .first()
    )
    if assignee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found.")

    previous_assignee = db.query(User).filter(User.id == alert.assigned_to_user_id).first()
    alert.assigned_to_user_id = assignee.id
    append_timeline(
        db=db,
        alert=alert,
        timestamp=utc_now(),
        action="assigned",
        user_name=current_user.name,
        details={
            "from_assignee": previous_assignee.name if previous_assignee else None,
            "to_assignee": assignee.name,
            "to_assignee_id": assignee.id,
        },
        note=payload.note,
    )
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert(
    db: Session,
    alert_id: int,
    payload: ResolveAlertRequest,
    current_user: User,
) -> Alert:
    alert = get_company_alert_or_404(db, alert_id, current_user)
    if alert.status != "acknowledged":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only acknowledged alerts can be resolved.",
        )

    now = utc_now()
    alert.status = "resolved"
    alert.resolved_at_utc = now
    alert.resolution_type = payload.resolution_type
    alert.resolution_root_cause = payload.root_cause
    alert.resolution_action_taken = payload.action_taken
    alert.resolution_preventive_measures = payload.preventive_measures
    alert.resolution_time_spent_minutes = payload.time_spent_minutes
    append_timeline(
        db=db,
        alert=alert,
        timestamp=now,
        action="resolved",
        user_name=current_user.name,
        details={
            "from_status": "acknowledged",
            "to_status": "resolved",
            "resolution_type": payload.resolution_type,
        },
    )
    db.commit()
    db.refresh(alert)
    return alert


def add_note(db: Session, alert_id: int, note: str, current_user: User) -> Alert:
    alert = get_company_alert_or_404(db, alert_id, current_user)
    append_timeline(
        db=db,
        alert=alert,
        timestamp=utc_now(),
        action="note_added",
        user_name=current_user.name,
        note=note,
    )
    db.commit()
    db.refresh(alert)
    return alert


def append_timeline(
    db: Session,
    alert: Alert,
    timestamp: datetime,
    action: str,
    user_name: str,
    details: dict | None = None,
    note: str | None = None,
) -> AlertTimeline:
    timeline = AlertTimeline(
        alert_id=alert.id,
        timestamp_utc=timestamp,
        action=action,
        user_name=user_name,
        source_raw_message_id=None,
        details_json=to_json_text(details) if details is not None else None,
        note=note,
    )
    db.add(timeline)
    db.flush()
    return timeline
