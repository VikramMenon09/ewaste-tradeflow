# ADR-002: Async Report Generation — BackgroundTasks with ARQ Upgrade Path

**Date:** March 2026
**Status:** Accepted

---

## Context

The platform generates PDF reports on demand (Country Profile, Trade Route Brief, Regional Summary). PDF generation via Puppeteer takes 10–30 seconds — too long for a synchronous HTTP response. An async pattern is required.

Two options were considered:

**Option A: FastAPI BackgroundTasks**
- Built into FastAPI. No additional infrastructure.
- Jobs run in the same process as the API server.
- Risk: jobs are lost if the API process restarts mid-generation.

**Option B: ARQ task queue**
- Async Python task queue backed by Redis.
- Workers are separate processes, providing isolation.
- Adds Redis as a hard dependency.

## Decision

Use **FastAPI BackgroundTasks for MVP**, with `tasks/report_tasks.py` written to ARQ's interface so migration is a one-day task.

## Rationale

- At MVP scale (200 concurrent users), report generation will be infrequent. Railway restart frequency is low. The probability of losing an in-flight report job is acceptable.
- Adding Redis as a hard dependency at MVP adds operational overhead disproportionate to the risk.
- A daily cleanup job resets `async_jobs` rows stuck in `processing` status for >2 hours, providing a safety net for the restart edge case.
- The isolation of job logic in `tasks/report_tasks.py` means the switch to ARQ requires changing only that file and the router — no schema changes, no frontend changes.

## Upgrade trigger

Switch to ARQ when either of these conditions is met:
- Concurrent report generation regularly exceeds 5 jobs/minute
- Railway deployments happen frequently enough that stuck-job cleanup is becoming a user-visible issue

## Consequences

- MVP ships without Redis as a dependency.
- `tasks/report_tasks.py` follows ARQ's function signature convention from day one.
- A background cleanup job must be scheduled to reset stuck jobs.
