from pathlib import Path

from app.database import Base, SessionLocal, engine
from app.ingest import ingest_sensor_messages, load_devices, seed_users
from app.models import Alert, AlertTimeline, Device, RawMessage, Reading, User


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


def main() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_users(db)
        devices_count = load_devices(db, DATA_DIR / "devices.json")
        summary = ingest_sensor_messages(db, DATA_DIR / "sensor_messages.json")
        db.commit()

        print("Seed completed")
        print(f"devices_loaded: {devices_count}")
        for key, value in summary.items():
            print(f"{key}: {value}")
        print_table_counts(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def print_table_counts(db) -> None:
    counts = {
        "users": db.query(User).count(),
        "devices": db.query(Device).count(),
        "raw_messages": db.query(RawMessage).count(),
        "readings": db.query(Reading).count(),
        "breached_readings": db.query(Reading).filter(Reading.breached_threshold.is_(True)).count(),
        "alerts": db.query(Alert).count(),
        "alert_timeline": db.query(AlertTimeline).count(),
        "invalid_raw_messages": db.query(RawMessage).filter(RawMessage.is_valid.is_(False)).count(),
    }
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
