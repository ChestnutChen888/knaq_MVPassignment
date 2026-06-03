from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)
    company = Column(String, nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class Device(Base):
    __tablename__ = "devices"

    device_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    company = Column(String, nullable=False, index=True)
    location = Column(String, nullable=False)
    timezone = Column(String, nullable=False)
    installed_date = Column(Date, nullable=True)
    floor_count = Column(Integer, nullable=True)
    reading_types_json = Column(Text, nullable=False)
    alert_thresholds_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class RawMessage(Base):
    __tablename__ = "raw_messages"

    id = Column(Integer, primary_key=True, index=True)
    dedupe_key = Column(String, unique=True, nullable=False, index=True)
    device_id = Column(String, nullable=True, index=True)
    message_type = Column(String, nullable=True, index=True)
    timestamp_utc = Column(DateTime, nullable=True, index=True)
    payload_json = Column(Text, nullable=False)
    is_valid = Column(Boolean, nullable=False, default=True)
    invalid_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=False, index=True)
    timestamp_utc = Column(DateTime, nullable=False, index=True)
    input_name = Column(String, nullable=False, index=True)
    input_value = Column(Float, nullable=True)
    is_expected_type = Column(Boolean, nullable=False)
    breached_threshold = Column(Boolean, nullable=False, default=False)
    threshold_value = Column(Float, nullable=True)
    threshold_direction = Column(String, nullable=True)
    source_raw_message_id = Column(Integer, ForeignKey("raw_messages.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=False, index=True)
    company = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    alert_type = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, index=True)
    triggered_at_utc = Column(DateTime, nullable=False, index=True)
    recovered_at_utc = Column(DateTime, nullable=True)
    reading_name = Column(String, nullable=True)
    reading_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="new", index=True)
    assigned_to_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    acknowledged_at_utc = Column(DateTime, nullable=True)
    resolved_at_utc = Column(DateTime, nullable=True)
    resolution_type = Column(String, nullable=True)
    resolution_root_cause = Column(Text, nullable=True)
    resolution_action_taken = Column(Text, nullable=True)
    resolution_preventive_measures = Column(Text, nullable=True)
    resolution_time_spent_minutes = Column(Integer, nullable=True)
    source_raw_message_id = Column(Integer, ForeignKey("raw_messages.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class AlertTimeline(Base):
    __tablename__ = "alert_timeline"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False, index=True)
    timestamp_utc = Column(DateTime, nullable=False, index=True)
    action = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    source_raw_message_id = Column(Integer, ForeignKey("raw_messages.id"), nullable=True, index=True)
    details_json = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
