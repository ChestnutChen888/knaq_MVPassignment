# Knaq IoT Alert Triage

This repo contains a full-stack alert triage system for IoT device messages.

The system ingests raw device messages, stores validated readings and alerts, and gives a building team a UI to acknowledge, assign, resolve, dismiss, reopen, and comment on alerts.

## Tech Stack

Backend:
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Python `zoneinfo`

Frontend:
- Next.js App Router
- TypeScript
- MUI
- Redux Toolkit + RTK Query
- Formik + Yup

Data:
- `data/devices.json`
- `data/sensor_messages.json`

## Run With Docker

Make sure Docker Desktop is running.

```powershell
docker compose up --build
```

Then open:

- Web app: `http://localhost:3000/alerts`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

Chrome is recommended for the frontend UI. Safari works for most flows, but some table and layout spacing may look less polished.

The API container seeds the SQLite database on startup. It loads devices, users, raw messages, readings, alerts, and timeline entries.

To stop the services:

```powershell
docker compose down
```

## Run Locally

### Backend

From the repo root:

```powershell
cd api
python -m pip install -r requirements.txt
python -m app.seed
python -m uvicorn app.main:app --reload
```

The API runs at:

```text
http://localhost:8000
```

### Frontend

In another terminal:

```powershell
cd web
npm install
npm run dev
```

The web app runs at:

```text
http://localhost:3000/alerts
```

Chrome is recommended for the frontend UI. Safari works for most flows, but some table and layout spacing may look less polished.

Create `web/.env.local` if needed:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_AUTH_TOKEN=token-brookfield-manager
```

## Seeded Users And Tokens

Requests use a bearer token. The token maps to a seeded user and company.

| Token | User | Role | Company |
|---|---|---|---|
| `token-brookfield-manager` | Alice Chen | Manager | Brookfield Properties |
| `token-brookfield-tech` | Bob Smith | Technician | Brookfield Properties |
| `token-brookfield-dispatcher` | Priya Patel | Dispatcher | Brookfield Properties |
| `token-hines-manager` | Lisa Wang | Manager | Hines |
| `token-hines-tech` | Mark Lee | Technician | Hines |

The frontend uses `token-brookfield-manager` by default.

## Test And Check Commands

Backend pytest:

```powershell
cd api
python -m pytest
```

Ingest smoke check:

```powershell
cd api
python -m app.seed
python -m app.check_ingest
```

API smoke check:

```powershell
cd api
python -m app.seed
python -m app.check_api
```

Frontend checks:

```powershell
cd web
npm run lint
npm run build
```

Note: `app.check_api` calls mutation endpoints, so it changes the database. Run `python -m app.seed` before it for repeatable results.




## System Workflow

The system follows this flow:

```text
device sends raw message
-> backend receives, validates, and cleans the message
-> valid data is stored in SQLite
-> alert messages create the alert queue
-> frontend shows alerts to the user
-> user triages the alert
-> every action is recorded in the timeline
```

Step by step:

1. Devices send raw messages.
   These messages can be readings, alerts, recoveries, duplicates, or malformed records.

2. The backend receives and cleans the messages.
   It validates required fields, checks that the device exists, detects duplicates, and keeps malformed messages in `raw_messages` instead of crashing.

3. Valid data is stored in SQLite.
   Raw payloads go into `raw_messages`, sensor values go into `readings`, alert workflow state goes into `alerts`, and audit history goes into `alert_timeline`.

4. Alert messages create the alert queue.
   A valid device alert creates a new alert row. That row starts with `status = new`.

5. The frontend shows the alert queue and detail page.
   The queue is for scanning, filtering, sorting, pagination, quick acknowledge, and bulk acknowledge. The detail page is for deeper triage.

6. Users process the alert.
   Depending on the alert status, a user can acknowledge, assign, resolve, dismiss, reopen, or add notes.

7. The backend records the history.
   Every successful mutation updates the alert row and appends a timeline entry. This makes the current state easy to query, while still preserving the full history of who did what and when.
The full lifecycle of an alert is:

```text
1. A device sends a raw alert message.
2. The backend ingests the message, validates it, and stores the raw payload.
3. If the message is valid, the backend creates a triage alert with status = new.
4. The alert appears in the frontend Alert Queue for users in the same company.
5. A user can acknowledge the alert, which moves it from new to acknowledged.
6. A manager can assign or reassign the alert to a team member.
7. Users can add notes during investigation, and each action is recorded in the timeline.
8. Once the issue is handled, a user resolves the alert with resolution details.
9. The resolved alert becomes read-only in the required workflow.
```

The same workflow can be summarized as:

```text
Device Alert
-> Ingest + Validate
-> Alert Created
-> Acknowledge
-> Assign / Add Notes
-> Resolve
```

Dismiss and reopen are supported as bonus side paths:

```text
new / acknowledged
-> Dismiss
-> dismissed

resolved / dismissed
-> Reopen
-> acknowledged
```


Dismiss is used when the alert should leave the active queue without resolution work. Reopen is used when a resolved or dismissed alert needs more work. After reopen, the alert returns to `acknowledged`, so it can be assigned, updated with notes, and resolved again.

Every action is synced to the timeline. The `alerts` table stores the latest state, and the `alert_timeline` table stores the full processing history.

The backend is the source of truth for all status transitions. The frontend renders contextual action buttons based on the current status, but invalid transitions are rejected by the API with a `409 Conflict` response.

## API Summary

All endpoints are scoped to the current user's company.

Read endpoints:

- `GET /alerts`
- `GET /alerts/{id}`
- `GET /devices`
- `GET /devices/{id}`
- `GET /devices/{id}/readings`
- `GET /users`

Alert mutations:

- `POST /alerts/{id}/acknowledge`
- `POST /alerts/{id}/assign`
- `POST /alerts/{id}/resolve`
- `POST /alerts/{id}/notes`
- `POST /alerts/{id}/dismiss`
- `POST /alerts/{id}/reopen`

`GET /alerts` supports:

- severity filters
- status filters
- device filter
- assignee filter
- search
- date range
- pagination with `page` and `page_size`
- sorting with `sort_by` and `sort_order`

Example:

```text
GET /alerts?page=1&page_size=10&sort_by=severity&sort_order=desc
```

`GET /devices/{id}/readings` expects `start` and `end` in the device local timezone. The response timestamps are also returned in that device local timezone.

Example:

```text
GET /devices/ELV-001/readings?start=2026-02-10T00:00:00&end=2026-02-13T23:59:59&breached_only=true
```


## Main Screens

### Alert Queue

The Alert Queue is the main triage workspace. It shows a company-scoped list of alerts loaded from the backend API, with a summary bar for alert counts by status. Users can filter alerts by status and severity, search by alert or device information, sort the table, and page through results.

Each alert row displays the severity, title, device, location, triggered time, current status, and assignee. New alerts can be acknowledged directly from the queue. The page also supports bulk acknowledge as a client-side fan-out over the existing acknowledge API. Loading, empty, and error states are handled explicitly so failed API calls are visible to the user.

### Alert Detail

The Alert Detail page shows the full context for a single alert. It includes the alert header, severity and status chips, device information, triggered reading versus threshold, assignment information, and a chronological timeline of system and user actions.

The available actions are contextual based on the alert status:

```text
New            -> Acknowledge, Assign, Dismiss
Acknowledged   -> Resolve, Assign, Dismiss
Resolved       -> Read-only, Reopen
Dismissed      -> Read-only, Reopen
```

Users can also add notes from the detail page. Notes are appended to the alert timeline through the backend API.

### Dialogs

The Assign Alert dialog loads real team members from `GET /users`, supports searching users, highlights the current assignee, and allows an optional assignment note.

The Resolve Alert dialog uses Formik and Yup for form state and validation. It collects the resolution type, root cause, action taken, optional preventive measures, and optional time spent before submitting to `POST /alerts/:id/resolve`.


## Theme

The frontend uses MUI `createTheme`.

It supports:

- light mode
- dark mode
- a toggle in the top-right UI chrome

Brand colors:

- Primary: `#EFC01A`
- Secondary: `#4B8189`
- Error: `#F44336`
- Warning: `#FFA726`
- Info: `#29B6F6`
- Success: `#66BB6A`

## Notes

SQLite was chosen because this is a local take-home project with a small dataset. The schema is still relational where it matters: alerts, readings, users, and timeline entries are queryable tables.

Device thresholds are kept as JSON on the device row for the MVP because they are static device config and mirror the source data. If thresholds became editable, versioned, or audited, the next step would be a separate `device_thresholds` table.
