from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import alerts, devices, users


app = FastAPI(title="Knaq IoT Alert Triage API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts.router)
app.include_router(devices.router)
app.include_router(users.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
