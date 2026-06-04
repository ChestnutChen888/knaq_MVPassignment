# Solution

## 1. Overview

This project implements an end-to-end IoT alert triage system.

The backend ingests raw device messages, validates them, stores readings and alerts, enforces company-scoped access, and exposes REST APIs. The frontend uses live HTTP calls to the backend and provides an alert queue, alert detail page, assignment workflow, resolution workflow, notes, timeline, pagination, sorting, bulk acknowledge, dismiss, and reopen.

The main goal of the system is to separate raw device signal processing from the human alert triage workflow.

---

## 2. Storage Choice

I used SQLite with SQLAlchemy for this take-home assignment. The dataset is small, the system needs to run locally, and SQLite avoids extra database setup for reviewers.

This is a good fit for the time box because it keeps the project easy to run while still allowing me to design relational tables and explain the schema clearly. In a production system, I would move to PostgreSQL because it provides stronger concurrency support, better indexing options, migrations, and production-grade reliability.

The schema separates two types of data:

1. Device signal data:

   * `raw_messages`
   * `readings`
   * `devices`

2. Human workflow data:

   * `alerts`
   * `alert_timeline`
   * `users`

This separation is important because raw device messages are append-only signal data, while alerts are workflow records that change state over time.

---

## 3. Main Tables

* `devices`: stores device metadata, company, timezone, reading types, and alert thresholds.
* `users`: stores seeded users, companies, roles, and bearer tokens.
* `raw_messages`: stores every unique raw message, including invalid messages.
* `readings`: stores parsed sensor readings and threshold breach results.
* `alerts`: stores the current alert state, assignee, resolution fields, and source raw message id.
* `alert_timeline`: stores the audit trail for each alert.

I store `company` directly on `alerts` so company-scoped alert queries are simple and clear. The device still remains the source of ownership during ingestion. When an alert is created from a device message, the alert copies the device's company.

The trade-off is that `company` is duplicated on the alert row. I chose this because alert queries are common, and filtering alerts by company should be simple and fast. In a larger system, I would still keep strong foreign keys and consider whether company ownership should always be derived from the device.

---

## 4. Device Thresholds

Device thresholds are stored as JSON on the `devices` row.

This was an intentional MVP choice. The assignment data already provides thresholds as device config, and these thresholds are relatively static. Storing them as JSON helped me move quickly within the time limit while still preserving the original config shape.

During ingestion, readings are evaluated once and the result is stored on the reading row:

* `breached_threshold`
* `threshold_value`
* `threshold_direction`

This means API reads do not need to re-evaluate historical readings.

The trade-off is that JSON threshold config is less flexible than a normalized table. If thresholds became editable, versioned, or auditable, I would move them into a `device_thresholds` table with fields such as:

* `device_id`
* `input_name`
* `direction`
* `value`
* `valid_from`
* `valid_to`

That would make threshold history easier to audit.

---

## 5. Ingestion and Validation

The seed command reads:

```text
data/devices.json
data/sensor_messages.json
```

For each message, the backend:

1. Builds a dedupe key.
2. Checks whether the message was already ingested.
3. Stores the raw payload.
4. Validates required fields.
5. Parses valid messages into readings, alerts, or recovery timeline entries.
6. Stores malformed messages as invalid raw messages instead of crashing.

Malformed messages are stored in `raw_messages` with:

* `is_valid = false`
* `invalid_reason`
* original payload

They do not enter `readings` or `alerts`.

This keeps ingestion resilient. One bad message does not stop the whole batch.

With more time, I would also add a separate invalid-message review API or admin page so operators could inspect malformed data and decide whether it needs manual repair or device-side fixes.

---

## 6. Duplicate Handling

The source data does not include message IDs, so I define duplicates using a deterministic dedupe key built from the full normalized message payload.

The dedupe logic:

* sorts JSON object keys
* normalizes reading `inputs` order
* hashes the canonical JSON form with SHA-256

This handles duplicate messages even if JSON key order or input order differs. Because the full payload is included in the hash, `device_id` is part of the dedupe input. That means the same reading shape from two different devices does not become a duplicate unless the entire payload, including `device_id`, is the same.

Duplicate protection exists in two places:

* application logic skips existing dedupe keys
* the database enforces uniqueness on `raw_messages.dedupe_key`

I chose this approach because using only `device_id + timestamp + message_type` would be too weak. A device could send more than one meaningful value at the same timestamp, or two messages with the same timestamp could still have different payloads.

The trade-off is that payload hashing is still an approximation. In a production system, I would prefer a device-provided message ID, a broker message ID, or an ingestion ID generated before persistence. That would provide stronger idempotency guarantees.

---

## 7. Threshold Breach Flagging

Readings are checked against the device's threshold config during ingestion.

The threshold keys follow the same shape as the source data:

```json
{
  "current_high": 95,
  "current_low": 5,
  "frequency_high": 65,
  "frequency_low": 55,
  "temperature_high": 130,
  "temperature_low": -5
}
```

For example, a `current` reading checks `current_high` and `current_low`.

If a reading breaches a threshold, the reading row stores:

* `breached_threshold = true`
* the threshold value that was crossed
* whether the breach was `above` or `below`

Breached readings are stored as signal data. They are not automatically mixed into the alert queue. The alert queue is based on device-reported alert messages.

I chose this separation because a reading breach and a device-reported alert are related but not the same thing. A breached reading is raw signal context, while an alert is part of the human triage workflow.

The breached reading results are exposed through `GET /devices/{id}/readings`, including the `breached_threshold`, `threshold_value`, and `threshold_direction` fields. The endpoint also supports `breached_only=true` so the reviewer can verify that threshold flagging works. I did not add a separate frontend device readings screen because the main product workflow for this project is alert triage.

The trade-off is that some breached readings may not appear as triage alerts. With more time, I would add a configurable rule engine that can decide whether a breached reading should create an alert automatically.

---

## 8. Alert Workflow Design

The lifecycle of one alert is:

```text
1. A device sends an alert message.
2. The backend ingests and validates the message.
3. The backend creates a row in the alerts table.
4. The alert starts with status = new.
5. The backend adds a created entry to the timeline.

6. A user sees the alert in the frontend.
7. The user acknowledges the alert.
8. The status changes to acknowledged.
9. The backend adds an acknowledged entry to the timeline.

10. A manager assigns the alert to a technician.
11. The alert stores the assigned user.
12. The backend adds an assigned entry to the timeline.

Assignment is also allowed before acknowledgment because it does not change the alert status.

13. A technician or manager adds a note.
14. The backend adds a note_added entry to the timeline.

Notes can be added at any point in the alert lifecycle so users can keep context during investigation, resolution, or follow-up.

15. The work is completed.
16. A user resolves the alert.
17. The status changes to resolved.
18. Resolution fields are saved.
19. The backend adds a resolved entry to the timeline.
```

The normal path is:

```text
new -> acknowledged -> resolved
```

Dismiss and reopen are also supported:

```text
new -> dismissed
acknowledged -> dismissed
resolved -> reopened -> acknowledged
dismissed -> reopened -> acknowledged
```

Reopened alerts return to `acknowledged` because the team has already seen the alert, but it now needs more work.

In the frontend, dismiss and reopen both show a confirmation dialog first. The mutation is only sent after the user confirms the action.

Every successful mutation appends a timeline entry. The `alerts` table stores the current state, while `alert_timeline` stores the history.

---

## 9. Server-Side Status Enforcement

The backend is the source of truth for status transitions.

The frontend shows the correct buttons for the current status, but the backend still enforces all rules. Invalid transitions return `409 Conflict`.

Examples:

* resolving a `new` alert returns `409`
* assigning a `resolved` or `dismissed` alert returns `409`
* dismissing a `resolved` alert returns `409`
* reopening a `new` alert returns `409`

This design protects the system even if there is a frontend bug, a stale browser tab, or a manual API call.

When the frontend receives a failed mutation, it does not update the UI as if the action succeeded. Most mutations call RTK Query's `.unwrap()` inside a `try/catch`. On failure, the UI shows a user-visible error message. On success, RTK Query invalidates the relevant `Alerts` and `Alert` tags and refetches the latest server state.

The trade-off is that the frontend must wait for the server response before showing the final state. I chose this because correctness is more important than assuming the client always knows the latest alert state.

---

## 10. Authentication and Company-Scoped APIs

Requests use bearer tokens.

Each token maps to a seeded user with:

* name
* role
* company

All list, detail, and mutation endpoints are scoped to the current user's company.

For list endpoints, the backend filters records by the current user's company. For detail and mutation endpoints, the backend uses helper functions such as company-scoped alert and device lookups. For example, an alert mutation first finds the alert by both `alert_id` and `current_user.company`. If no matching alert is found, the API returns `404`.

This means a user cannot read or modify another company's alerts even if they guess an alert ID.

For assignment, the backend also checks that the assignee belongs to the same company. This prevents assigning one company's alert to another company's user.

Cross-company resources return `404` instead of `403`. I chose this to avoid leaking whether another company's alert or device exists.

---

## 11. Timezone Handling

Raw message timestamps are epoch milliseconds in UTC.

The backend stores timestamps in UTC. For `GET /devices/{id}/readings`, `start` and `end` are interpreted in the device's local timezone. The backend converts those local times to UTC for querying, then converts response timestamps back to the device's local timezone.

This keeps timezone logic on the server and avoids relying on the browser's local timezone.

---

## 12. API Design

Main read endpoints:

* `GET /alerts`
* `GET /alerts/{id}`
* `GET /devices`
* `GET /devices/{id}`
* `GET /devices/{id}/readings`
* `GET /users`

Main mutation endpoints:

* `POST /alerts/{id}/acknowledge`
* `POST /alerts/{id}/assign`
* `POST /alerts/{id}/resolve`
* `POST /alerts/{id}/notes`
* `POST /alerts/{id}/dismiss`
* `POST /alerts/{id}/reopen`

`GET /alerts` supports:

* company scoping
* severity filters
* status filters
* device filter
* assignee filter
* search
* date range
* pagination with `page` and `page_size`
* sorting with `sort_by` and `sort_order`

`GET /devices/{id}/readings` supports:

* local-time `start` and `end`
* `breached_only=true`
* threshold breach fields in the response

---

## 13. Frontend Design

The frontend is built with Next.js App Router, TypeScript, MUI, Redux Toolkit, RTK Query, Formik, and Yup.

Redux is used mainly to host the RTK Query API slice. I did not add extra Redux slices because most of the remaining state is local UI state and does not need to be shared globally.

RTK Query owns server state and caching for:

* `GET /alerts`
* `GET /alerts/{id}`
* `GET /devices`
* `GET /users`
* alert mutations such as acknowledge, assign, resolve, notes, dismiss, and reopen

The API slice defines cache tags such as `Alerts`, `Alert`, `Devices`, and `Users`. List mutations invalidate `Alerts`, and detail mutations also invalidate the specific `Alert` id. This keeps the queue and detail page synchronized after a workflow action.

Local React state owns UI-only state:

* status filter
* severity filter
* search text
* sort selection
* current page and page size
* selected alert ids for bulk acknowledge
* dialog open or closed state
* local form state through Formik
* theme mode

This keeps backend data and UI-only state separate.

The frontend does not use mock data. It calls the backend API with a configurable API base URL and a bearer token from environment variables.

The current user shown in the UI is based on the configured token. This keeps authentication simple for the take-home while still showing how multi-tenant behavior works.

---

## 14. Frontend Features

Alert Queue:

* summary counts by status
* status filter
* severity filter
* search
* sort control
* pagination
* alert table
* quick acknowledge
* bulk acknowledge
* loading, empty, and error states

Alert Detail:

* alert header
* severity and status chips
* device context
* metric card
* assignment card
* add note form
* timeline
* contextual actions

Dialogs:

* Assign Alert dialog loads team members from `GET /users`.
* Resolve Alert dialog uses Formik + Yup validation.

Theme:

* MUI `createTheme`
* light mode
* dark mode
* toggle in the UI
* provided brand colors

---

## 15. Error Handling

The frontend does not silently ignore failures.

Read failures show an MUI error alert with a retry button. Mutation failures show user-visible errors: simple action failures use an alert message, and dialog/form failures use Formik status or inline form errors. Successful mutations invalidate RTK Query cache so the UI refetches the latest server state.

I used pessimistic updates instead of optimistic UI updates. The UI waits for the server to accept the mutation before showing the final status. I did not use RTK Query's `onQueryStarted` optimistic update hooks in this version.

For example:

* acknowledge, dismiss, reopen, assign, resolve, and add note call `.unwrap()`
* success invalidates RTK Query tags and refetches server data
* failure stays on the current UI state and shows an error message
* invalid transitions from the backend return `409 Conflict`

This is simpler and safer for this workflow because the backend owns the status transition rules.

The trade-off is that the UI may feel slightly less instant than a fully optimistic update. With more time, I would add optimistic updates only for low-risk actions and make sure they roll back correctly on server rejection.

---

## 16. Testing

I added both smoke checks and a pytest integration test.

Smoke scripts:

```text
python -m app.check_ingest
python -m app.check_api
```

Pytest:

```text
api/tests/test_api_workflow.py
```

The checks cover:

* ingestion counts
* malformed messages
* duplicate handling
* threshold breach logic
* company scoping
* 401 authentication failures
* alert workflow mutations
* invalid transitions returning `409`
* dismiss and reopen
* pagination and sorting
* breached readings API

Frontend validation:

```text
npm run lint
npm run build
```

---

## 17. Additional Libraries

Backend libraries:

* `fastapi`: API framework.
* `uvicorn`: local ASGI server.
* `sqlalchemy`: ORM and schema mapping.
* `pydantic`: request and response validation.
* `tzdata`: timezone support on systems that need IANA timezone data.
* `httpx`: required by FastAPI's test client stack.
* `pytest`: backend integration test runner.

Frontend libraries:

* `@mui/material`, `@mui/icons-material`, `@emotion/react`, `@emotion/styled`: UI components, theme support, and icons.
* `@reduxjs/toolkit` and `react-redux`: RTK Query API state and Redux provider setup.
* `formik`: form state for assign, resolve, and notes.
* `yup`: validation rules for form inputs.
* `dayjs`: readable date and relative-time formatting.

I did not add ECharts because analytics was not implemented. I kept the dependency set focused on the required workflow.

---

## 18. Docker

The project includes Docker support.

```powershell
docker compose up --build
```

This starts:

* FastAPI API on `http://localhost:8000`
* Next.js web app on `http://localhost:3000`

The API container seeds the SQLite database on startup.

I also verified Docker locally with:

* `docker compose config`
* `docker compose up --build`
* `GET /health`
* `GET /alerts`
* browser access to the frontend

---

## 19. What I Would Improve With More Time



There are several areas I would improve with more time.


**Database and schema.** SQLite works well for local setup, but I would switch to PostgreSQL for production — it handles concurrency better and supports proper indexing and operational tooling. I would also add Alembic migrations so schema changes are versioned rather than rebuilt from scratch on each seed. On the schema side, if device thresholds ever became editable or auditable, I would pull them out of the JSON field on `devices` and into a proper `device_thresholds` table with `valid_from` and `valid_to` columns.

**Ingestion and signal processing.** Recovery handling is currently best-effort. A recovery message is matched to the most recent alert with the same device, alert type, and severity — but it only sets `recovered_at` and adds a timeline entry. It does not auto-resolve the alert, because device recovery and human resolution are different things. That said, there is one edge case I would fix: if an alert is already resolved and a recovery message arrives later, I would not append it to the completed workflow. Instead, I would store it as raw signal data. That keeps the human timeline clean. I would also add a simple rule engine so breached readings can automatically create triage alerts when no device-reported alert message shows up.

**Observability and tooling.** The backend already stores invalid messages with their rejection reasons. The next step would be a small admin page so operators can review malformed payloads and decide if the fix is on the device side or needs manual repair. I would also wire up a CI pipeline to run backend tests, ingest checks, API checks, and frontend lint and build on every commit.

**Frontend.** For low-risk actions like notes and assignment changes, I would add optimistic UI updates using RTK Query's `onQueryStarted` hook, with rollback on server rejection. I would also add component tests covering the alert queue, dialogs, mutation failures, and empty and error states. Given more time, I would build out the analytics dashboard — MTTR, alert volume trends, resolution breakdown, and severity charts with ECharts.


---

## 20. AI Tool Disclosure

I used AI coding assistance during this project for planning, implementation help, debugging, test ideas, and documentation drafting.

I used it to help:

* draft parts of the FastAPI and Next.js implementation
* debug threshold matching, dedupe behavior, and API response shapes
* plan smoke checks and pytest coverage
* review UI workflow decisions
* draft and revise README and SOLUTION documentation

I designed the overall architecture, data schema, API behavior, and workflow decisions. I also reviewed and adjusted generated code, tested API responses, checked frontend behavior, and made the final decisions around schema design, workflow rules, threshold handling, duplicate handling, and trade-offs.
