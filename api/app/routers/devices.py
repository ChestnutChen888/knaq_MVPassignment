from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api_utils import (
    get_company_device_or_404,
    json_text_to_dict,
    json_text_to_list,
    local_to_utc_naive,
    utc_naive_to_local_iso,
)
from app.auth import get_current_user
from app.database import get_db
from app.models import Device, Reading, User
from app.schemas import DeviceReadingsResponse, DeviceResponse


router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceResponse])
def list_devices(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[DeviceResponse]:
    devices = (
        db.query(Device)
        .filter(Device.company == current_user.company)
        .order_by(Device.device_id.asc())
        .all()
    )
    return [device_to_response(device, include_config=False) for device in devices]


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DeviceResponse:
    device = get_company_device_or_404(db, device_id, current_user)
    return device_to_response(device, include_config=True)


@router.get("/{device_id}/readings", response_model=DeviceReadingsResponse)
def get_device_readings(
    device_id: str,
    start: str,
    end: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    breached_only: bool = False,
    input_name: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
) -> DeviceReadingsResponse:
    device = get_company_device_or_404(db, device_id, current_user)
    start_utc = local_to_utc_naive(start, device.timezone)
    end_utc = local_to_utc_naive(end, device.timezone)

    query = (
        db.query(Reading)
        .filter(Reading.device_id == device.device_id)
        .filter(Reading.timestamp_utc >= start_utc)
        .filter(Reading.timestamp_utc < end_utc)
    )
    if breached_only:
        query = query.filter(Reading.breached_threshold.is_(True))
    if input_name:
        query = query.filter(Reading.input_name == input_name)

    readings = query.order_by(Reading.timestamp_utc.asc(), Reading.id.asc()).limit(limit).all()
    return DeviceReadingsResponse(
        device_id=device.device_id,
        timezone=device.timezone,
        items=[
            {
                "timestamp": utc_naive_to_local_iso(reading.timestamp_utc, device.timezone),
                "input_name": reading.input_name,
                "input_value": reading.input_value,
                "is_expected_type": reading.is_expected_type,
                "breached_threshold": reading.breached_threshold,
                "threshold_value": reading.threshold_value,
                "threshold_direction": reading.threshold_direction,
            }
            for reading in readings
        ],
    )


def device_to_response(device: Device, include_config: bool) -> dict:
    response = {
        "device_id": device.device_id,
        "name": device.name,
        "type": device.type,
        "company": device.company,
        "location": device.location,
        "timezone": device.timezone,
        "installed_date": device.installed_date.isoformat() if device.installed_date else None,
        "floor_count": device.floor_count,
    }
    if include_config:
        response["reading_types"] = json_text_to_list(device.reading_types_json)
        response["alert_thresholds"] = json_text_to_dict(device.alert_thresholds_json)
    return response
