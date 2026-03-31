"""Report generation service.

Runs as a FastAPI BackgroundTask.  Workflow:
  1. Mark the async_jobs row as 'processing'.
  2. Build the internal frontend render URL with base64-encoded filter params.
  3. POST to the Puppeteer microservice to render a PDF.
  4. Upload the PDF to S3.
  5. Generate a 24-hour presigned download URL.
  6. Mark the job as 'complete' with the presigned URL.
  7. On any failure, mark the job as 'failed' with the error message.
"""

from __future__ import annotations

import base64
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

_PRESIGNED_URL_TTL_SECONDS = 86400  # 24 hours


async def generate_report(
    job_id: str,
    report_type: str,
    params: dict,
    # A fresh session is opened inside the function so it can be called as a
    # BackgroundTask without sharing the request-scoped session.
) -> None:
    """Generate a PDF report and update the async_jobs row on completion.

    This function is designed to run as a FastAPI BackgroundTask and therefore
    opens its own database session.
    """
    async with AsyncSessionLocal() as db:
        try:
            await _set_job_status(db, job_id, "processing", started_at=datetime.now(tz=timezone.utc))

            # 1. Build the internal render URL
            encoded_params = base64.urlsafe_b64encode(
                json.dumps(params, default=str).encode()
            ).decode()
            render_url = (
                f"{settings.FRONTEND_URL}/internal/report-view"
                f"?type={report_type}&filters={encoded_params}"
            )

            # 2. POST to the Puppeteer microservice
            pdf_bytes = await _call_puppeteer(render_url)

            # 3. Upload to S3
            s3_key = f"reports/{job_id}.pdf"
            await _upload_to_s3(pdf_bytes, s3_key)

            # 4. Generate presigned URL
            presigned_url = _generate_presigned_url(s3_key)
            expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=_PRESIGNED_URL_TTL_SECONDS)

            # 5. Mark complete
            await _set_job_status(
                db,
                job_id,
                "complete",
                output_url=presigned_url,
                output_expires_at=expires_at,
                completed_at=datetime.now(tz=timezone.utc),
            )
            await db.commit()
            logger.info("Report job %s completed successfully", job_id)

        except Exception as exc:
            logger.exception("Report job %s failed: %s", job_id, exc)
            try:
                await _set_job_status(
                    db,
                    job_id,
                    "failed",
                    error_message=str(exc),
                    completed_at=datetime.now(tz=timezone.utc),
                )
                await db.commit()
            except Exception:
                logger.exception("Failed to update job %s to failed state", job_id)


# ── Private helpers ───────────────────────────────────────────────────────────

async def _set_job_status(
    db: AsyncSession,
    job_id: str,
    status: str,
    *,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    output_url: str | None = None,
    output_expires_at: datetime | None = None,
    error_message: str | None = None,
) -> None:
    """Update async_jobs row with new status and optional fields."""
    sets = ["status = :status"]
    bind: dict = {"job_id": job_id, "status": status}

    if started_at is not None:
        sets.append("started_at = :started_at")
        bind["started_at"] = started_at
    if completed_at is not None:
        sets.append("completed_at = :completed_at")
        bind["completed_at"] = completed_at
    if output_url is not None:
        sets.append("output_url = :output_url")
        bind["output_url"] = output_url
    if output_expires_at is not None:
        sets.append("output_expires_at = :output_expires_at")
        bind["output_expires_at"] = output_expires_at
    if error_message is not None:
        sets.append("error_message = :error_message")
        bind["error_message"] = error_message

    sql = text(f"UPDATE async_jobs SET {', '.join(sets)} WHERE id = :job_id::uuid")
    await db.execute(sql, bind)


async def _call_puppeteer(render_url: str) -> bytes:
    """POST to the Puppeteer service and return the PDF bytes."""
    payload = {"url": render_url, "key": settings.PUPPETEER_INTERNAL_KEY}
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(settings.PUPPETEER_SERVICE_URL, json=payload)
        response.raise_for_status()
        return response.content


async def _upload_to_s3(pdf_bytes: bytes, s3_key: str) -> None:
    """Upload PDF bytes to the configured S3 bucket."""
    s3_kwargs: dict = {
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
    }
    if settings.S3_ENDPOINT_URL:
        s3_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

    # boto3 is synchronous; run in a thread pool in production or use aioboto3
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_upload, pdf_bytes, s3_key, s3_kwargs)


def _sync_upload(pdf_bytes: bytes, s3_key: str, s3_kwargs: dict) -> None:
    """Blocking S3 upload — called via run_in_executor."""
    s3 = boto3.client("s3", **{k: v for k, v in s3_kwargs.items() if v is not None})
    s3.put_object(
        Bucket=settings.S3_BUCKET,
        Key=s3_key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )


def _generate_presigned_url(s3_key: str) -> str:
    """Generate a presigned S3 URL valid for 24 hours."""
    s3_kwargs: dict = {
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
    }
    if settings.S3_ENDPOINT_URL:
        s3_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

    s3 = boto3.client("s3", **{k: v for k, v in s3_kwargs.items() if v is not None})
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": s3_key},
        ExpiresIn=_PRESIGNED_URL_TTL_SECONDS,
    )
