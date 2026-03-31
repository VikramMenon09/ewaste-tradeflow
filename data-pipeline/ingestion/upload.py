"""
Upload validated DataFrames to S3 as immutable Parquet files.

Raw data in S3 is never overwritten — each run writes a new timestamped file.
The S3 key structure is:
    raw/{source}/year={year}/hs={hs_code}/batch_{iso_timestamp}.parquet

For sources without HS codes (OECD, UN Monitor, WB Governance):
    raw/{source}/year={year}/batch_{iso_timestamp}.parquet
"""

import logging
import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)


def upload_dataframe(
    df: "pd.DataFrame",
    source: str,
    year: int,
    hs_code: Optional[str] = None,
    bucket: Optional[str] = None,
    dry_run: bool = False,
) -> str:
    """
    Serialize df to Parquet and upload to S3.

    Args:
        df: Normalized and validated DataFrame
        source: Source identifier (e.g. 'comtrade', 'oecd', 'un_monitor')
        year: Data year
        hs_code: HS code if applicable (Comtrade only)
        bucket: S3 bucket name (defaults to S3_BUCKET env var)
        dry_run: If True, log what would be uploaded but don't actually upload

    Returns:
        S3 key of the uploaded file (e.g. 'raw/comtrade/year=2022/hs=8548/batch_...')
    """
    import pandas as pd

    bucket = bucket or os.environ["S3_BUCKET"]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if hs_code:
        key = f"raw/{source}/year={year}/hs={hs_code}/batch_{timestamp}.parquet"
    else:
        key = f"raw/{source}/year={year}/batch_{timestamp}.parquet"

    if dry_run:
        logger.info("DRY RUN: would upload %d rows to s3://%s/%s", len(df), bucket, key)
        return key

    buffer = BytesIO()
    df.to_parquet(buffer, index=False, compression="snappy")
    buffer.seek(0)

    s3_client = _get_s3_client()
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=buffer.getvalue(),
        ContentType="application/octet-stream",
        Metadata={
            "source": source,
            "year": str(year),
            "row_count": str(len(df)),
            "uploaded_at": timestamp,
        },
    )

    logger.info("Uploaded %d rows to s3://%s/%s", len(df), bucket, key)
    return key


def _get_s3_client():
    """Build a boto3 S3 client, supporting S3-compatible endpoints (MinIO, R2)."""
    import boto3

    kwargs: dict = {}
    endpoint_url = os.environ.get("S3_ENDPOINT_URL")
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url

    return boto3.client(
        "s3",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        **kwargs,
    )
