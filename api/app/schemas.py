from typing import Literal

from pydantic import BaseModel, Field


AlertStatus = Literal["new", "acknowledged", "resolved", "dismissed"]
AlertSeverity = Literal["warning", "critical"]
ResolutionType = Literal["fixed", "false_alarm", "known_issue", "deferred", "cannot_reproduce"]


class UserResponse(BaseModel):
    id: str
    name: str
    email: str | None = None
    role: str
    company: str | None = None


class DeviceResponse(BaseModel):
    device_id: str
    name: str
    type: str
    company: str | None = None
    location: str
    timezone: str
    installed_date: str | None = None
    floor_count: int | None = None
    reading_types: list[str] | None = None
    alert_thresholds: dict | None = None


class AlertListItem(BaseModel):
    id: int
    title: str
    device_id: str
    device_name: str
    device_location: str
    alert_type: str
    severity: str
    status: str
    assigned_to: UserResponse | None
    triggered_at: str
    recovered_at: str | None = None
    reading_name: str | None = None
    reading_value: float | None = None
    threshold_value: float | None = None


class AlertListResponse(BaseModel):
    items: list[AlertListItem]
    total: int
    summary: dict[str, int]
    page: int = 1
    page_size: int = 20


class TimelineEntryResponse(BaseModel):
    id: int
    timestamp: str
    action: str
    user_name: str
    source_raw_message_id: int | None = None
    details: dict | None = None
    note: str | None = None
    created_at: str


class AlertResolutionResponse(BaseModel):
    type: str | None = None
    root_cause: str | None = None
    action_taken: str | None = None
    preventive_measures: str | None = None
    time_spent_minutes: int | None = None


class AlertDetailResponse(AlertListItem):
    device: DeviceResponse
    acknowledged_at: str | None = None
    resolved_at: str | None = None
    resolution: AlertResolutionResponse | None = None
    timeline: list[TimelineEntryResponse]


class ReadingResponse(BaseModel):
    timestamp: str
    input_name: str
    input_value: float | None
    is_expected_type: bool
    breached_threshold: bool
    threshold_value: float | None = None
    threshold_direction: str | None = None


class DeviceReadingsResponse(BaseModel):
    device_id: str
    timezone: str
    items: list[ReadingResponse]


class AssignAlertRequest(BaseModel):
    assignee_id: str
    note: str | None = None


class ResolveAlertRequest(BaseModel):
    resolution_type: ResolutionType
    root_cause: str = Field(min_length=1)
    action_taken: str = Field(min_length=1)
    preventive_measures: str | None = None
    time_spent_minutes: int | None = Field(default=None, ge=0)


class AddNoteRequest(BaseModel):
    note: str = Field(min_length=1)
