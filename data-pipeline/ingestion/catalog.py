"""
Write pipeline run metadata to the data_sources and pipeline_runs tables.

Maintains an audit trail of every ingestion run: which source, when it ran,
how many records were fetched, which S3 keys were written, and whether it
succeeded or failed. This is the 'source_id' FK that every data record carries.
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


@contextmanager
def get_db_conn():
    """Yield a psycopg2 connection from DATABASE_SYNC_URL."""
    conn = psycopg2.connect(os.environ["DATABASE_SYNC_URL"])
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def start_pipeline_run(
    source_name: str,
    run_type: str = "scheduled",
    triggered_by: Optional[str] = None,
) -> int:
    """
    Insert a pipeline_runs row and return its ID.
    Call this at the start of each ingestion run.

    Args:
        source_name: e.g. 'comtrade', 'oecd', 'un_monitor'
        run_type: 'scheduled' or 'manual'
        triggered_by: username or service name that triggered the run

    Returns:
        pipeline_run_id to pass to complete_pipeline_run()
    """
    sql = """
        INSERT INTO pipeline_runs
            (source_name, run_type, status, started_at, triggered_by)
        VALUES (%s, %s, 'started', NOW(), %s)
        RETURNING id
    """
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (source_name, run_type, triggered_by))
            run_id = cur.fetchone()[0]

    logger.info("Started pipeline run %d for source '%s'", run_id, source_name)
    return run_id


def complete_pipeline_run(
    run_id: int,
    status: str,
    records_fetched: int = 0,
    records_written: int = 0,
    s3_prefix: Optional[str] = None,
    error_log: Optional[str] = None,
) -> None:
    """
    Update a pipeline_runs row on completion (success or failure).

    Args:
        run_id: ID returned by start_pipeline_run()
        status: 'success', 'partial', or 'failed'
        records_fetched: Total records retrieved from the API
        records_written: Total records written to S3 (after filtering)
        s3_prefix: S3 prefix for all files written in this run
        error_log: Error traceback if status is 'failed' or 'partial'
    """
    sql = """
        UPDATE pipeline_runs SET
            status = %s,
            records_fetched = %s,
            records_written = %s,
            s3_prefix = %s,
            error_log = %s,
            completed_at = NOW()
        WHERE id = %s
    """
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (
                status, records_fetched, records_written,
                s3_prefix, error_log, run_id,
            ))

    logger.info(
        "Completed pipeline run %d: status=%s fetched=%d written=%d",
        run_id, status, records_fetched, records_written,
    )


def upsert_data_source(
    name: str,
    url: str,
    vintage_year: int,
    methodology_notes: str = "",
) -> int:
    """
    Insert or update a data_sources row and return its ID.
    Used as the source_id FK on all data records.

    Args:
        name: Human-readable source name (e.g. 'UN Global E-waste Monitor 2024')
        url: Source URL
        vintage_year: Publication year of this edition of the source
        methodology_notes: Free text notes on methodology and known limitations

    Returns:
        data_source_id
    """
    sql = """
        INSERT INTO data_sources (name, url, vintage_year, accessed_date, methodology_notes)
        VALUES (%s, %s, %s, NOW(), %s)
        ON CONFLICT (name, vintage_year) DO UPDATE SET
            url = EXCLUDED.url,
            accessed_date = NOW(),
            methodology_notes = EXCLUDED.methodology_notes
        RETURNING id
    """
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (name, url, vintage_year, methodology_notes))
            source_id = cur.fetchone()[0]

    return source_id


def get_last_successful_run(source_name: str) -> Optional[datetime]:
    """
    Return the completed_at timestamp of the last successful run for a source.
    Used to implement the 'last_fetched cursor' so re-runs skip already-fetched data.

    Returns None if no successful run has been recorded.
    """
    sql = """
        SELECT completed_at FROM pipeline_runs
        WHERE source_name = %s AND status = 'success'
        ORDER BY completed_at DESC
        LIMIT 1
    """
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (source_name,))
            row = cur.fetchone()
            return row[0] if row else None
