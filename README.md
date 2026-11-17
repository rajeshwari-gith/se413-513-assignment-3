# Assignment 3 — Integration and System Testing (Starter Code)

This is the starter code for SE 413/513 Assignment 3. The **Course
Registration System** from Assignments 1–2 is now a small, complete
system: an HTTP API, a service, and a SQLite database, built on the same
`can_register()` and `calculate_registration_fee()` you tested before.
Everything in `src/` and `serve.py` is provided and **must not be
modified**. `SPEC.md` is the specification your tests check against.

## Project layout

```
assignment-3/
|-- src/
|   |-- registration.py      can_register(), calculate_registration_fee() (Assignments 1-2)
|   |-- db.py                schema, connect(), seed data
|   |-- repository.py        all SQL (RegistrationRepository)
|   |-- service.py           RegistrationService: enroll(), withdraw(), schedule()
|   |-- notifier.py          OutboxNotifier (used by serve.py)
|   |-- errors.py            exceptions shared by the components
|   `-- api.py               Flask HTTP API
|-- serve.py                 runs the whole system as one process
|-- SPEC.md                  requirements REQ-1..8, HTTP API, seed data
|-- tests/
|   |-- integration/conftest.py       (implement your fixtures here)
|   |-- integration/test_integration.py (implement your tests here)
|   |-- system/conftest.py            (PROVIDED: starts serve.py for each test)
|   `-- system/test_system.py         (implement your tests here)
|-- pyproject.toml
|-- requirements.txt
`-- README.md
```

## Setup

1. (Recommended) Create and activate a virtual environment:

   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

## Running the system by hand

```
python serve.py
```

prints `READY url=http://127.0.0.1:8000 outbox=...`. In a second terminal:

```
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/enrollments -H 'X-API-Key: registrar-key' \
     -H 'Content-Type: application/json' -d '{"student_id": "S01", "course_code": "SE413"}'
curl http://127.0.0.1:8000/students/S01/schedule -H 'X-API-Key: registrar-key'
```

(On Windows PowerShell, use `curl.exe` and escape the inner quotes, or
use Python's `requests`.) Every start uses a fresh database seeded as in
`SPEC.md`, unless you pass `--db <file>`.

## Running the tests

From the project root:

```
pytest                    # everything
pytest -m integration     # integration tests only
pytest -m system          # system tests only (each starts its own server)
```

## Notes

- Do not modify `src/` or `serve.py`. The starter contains **one known
  defect** (Section 4(d) of the assignment): document it with a test, do
  not fix it.
- Modules in `src/` are importable directly in your tests (no `src.`
  prefix), e.g. `from repository import RegistrationRepository`.
- `xfail_strict = true` is set in `pyproject.toml`: an `xfail` test that
  unexpectedly passes is reported as a failure.
- System tests must not import from `src/`: they see only HTTP and the
  outbox, through the provided `system` fixture.

## 4(a) Integration points

| IP | Components | Communication | Possible disagreement |
|---|---|---|---|
| IP1 | HTTP client ↔ api.py | HTTP (JSON, API key header) | Body format: client sends a number or a missing field, API expects two short strings |
| IP2 | api.py ↔ RegistrationService | Python calls + exceptions | Which exception maps to which status code (e.g. CourseFull → 409) |
| IP3 | RegistrationService ↔ RegistrationRepository | Python calls + return values + exceptions | What a method does: `remove_enrollment(student, course)` should remove only one student's row |
| IP4 | RegistrationRepository ↔ SQLite | SQL | Whether the SQL filters on the right columns |
| IP5 | RegistrationService ↔ notifier | Python calls | Argument order and meaning (fee vs. reason) |

## 4(d) Known defect

`remove_enrollment()` deletes `WHERE course_code = ?` without checking `student_id`,
so when one student withdraws, every student in that course is removed.
A unit test of `withdraw()` with a mocked repository would pass, because the mock
just returns `True` and the service does call `remove_enrollment()` and `release_seat()`
with the correct arguments. The bug is in the real SQL, which the mock replaces.

## 5(c) Why concurrency needs a system test

The race only happens in the running server, where each request runs on its own
thread with its own database connection. An integration test uses one connection
in one process, so the requests never actually compete for the seats.
