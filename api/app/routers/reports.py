"""Reports router — async PDF report generation.

Endpoints:
  POST /reports/generate  — enqueue an async PDF generation job
  GET  /reports/{job_id}  — poll job status, get download URL when done
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_optional_user
from app.middleware.rate_limit import limiter
from app.models.db import AsyncJob
from app.models.schemas import ReportGenerateRequest, ReportGenerateResponse, ReportStatusResponse
from app.services.report_generator import generate_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/generate",
    response_model=ReportGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def generate_report_endpoint(
    request: Request,
    body: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] | None = Depends(get_optional_user),
) -> ReportGenerateResponse:
    """Enqueue an async PDF generation job.

    Returns immediately with a job_id and poll URL.  The actual PDF is
    generated in the background via the Puppeteer microservice.

    Rate limited to 10 requests per minute per IP address.
    """
    job_id = uuid.uuid4()
    auth0_user_id = user.get("sub") if user else None

    stmt = insert(AsyncJob).values(
        id=job_id,
        auth0_user_id=auth0_user_id,
        job_type=body.report_type,
        status="queued",
        params=body.params,
    )
    await db.execute(stmt)
    await db.commit()

    background_tasks.add_task(
        generate_report,
        job_id=str(job_id),
        report_type=body.report_type,
        params=body.params,
    )

    return ReportGenerateResponse(
        job_id=job_id,
        poll_url=f"/api/v1/reports/{job_id}",
        estimated_wait_seconds=30,
    )


@router.get("/{job_id}", response_model=ReportStatusResponse)
@limiter.limit("30/minute")
async def get_report_status(
    request: Request,
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReportStatusResponse:
    """Poll the status of an async PDF generation job.

    Returns the job status and, when complete, a presigned S3 download URL
    valid for 24 hours.

    Rate limited to 30 requests per minute per IP address.
    """
    stmt = select(AsyncJob).where(AsyncJob.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report job '{job_id}' not found",
        )

    return ReportStatusResponse(
        job_id=job.id,
        status=job.status,
        download_url=job.output_url,
        expires_at=job.output_expires_at,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
