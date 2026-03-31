#!/usr/bin/env python3
"""
EWasteTradeFlow — ingestion pipeline CLI.

Usage:
    python run_ingestion.py --source comtrade --year 2022
    python run_ingestion.py --source all --year 2022
    python run_ingestion.py --source comtrade --year 2022 --dry-run
    python run_ingestion.py --source un_monitor --file /path/to/un_monitor_2024.xlsx

Sources:
    comtrade      — UN Comtrade Plus API (bilateral trade flows)
    oecd          — OECD.Stat API (transboundary waste movements)
    un_monitor    — UN Global E-waste Monitor (manual Excel ingestion)
    wb_governance — World Bank Governance Indicators API
    basel         — Basel Convention status (static reference, manual)
    all           — Run all automated sources (not un_monitor or basel)
"""

import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

# Load environment variables from .env file if present
load_dotenv(Path(__file__).parent.parent.parent / ".env")

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger("ewaste.ingestion")

AUTOMATED_SOURCES = ["comtrade", "oecd", "wb_governance"]
MANUAL_SOURCES = ["un_monitor", "basel"]
ALL_SOURCES = AUTOMATED_SOURCES + MANUAL_SOURCES


@click.command()
@click.option(
    "--source",
    type=click.Choice(ALL_SOURCES + ["all"], case_sensitive=False),
    required=True,
    help="Data source to ingest. Use 'all' for all automated sources.",
)
@click.option(
    "--year",
    type=int,
    default=None,
    help="Data year to fetch. Defaults to previous calendar year.",
)
@click.option(
    "--start-year",
    type=int,
    default=None,
    help="Start of year range for historical backfill (inclusive).",
)
@click.option(
    "--end-year",
    type=int,
    default=None,
    help="End of year range for historical backfill (inclusive).",
)
@click.option(
    "--file",
    type=click.Path(exists=True),
    default=None,
    help="Path to source file (required for un_monitor and basel sources).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Log what would be done without uploading to S3 or writing to DB.",
)
@click.option(
    "--run-type",
    type=click.Choice(["scheduled", "manual"], case_sensitive=False),
    default="manual",
    help="Whether this is a scheduled or manual run (for audit log).",
)
@click.option(
    "--triggered-by",
    default=None,
    help="Username or service name triggering this run (for audit log).",
)
def main(
    source: str,
    year: Optional[int],
    start_year: Optional[int],
    end_year: Optional[int],
    file: Optional[str],
    dry_run: bool,
    run_type: str,
    triggered_by: Optional[str],
) -> None:
    """Run the EWasteTradeFlow data ingestion pipeline."""

    if dry_run:
        console.print("[yellow]DRY RUN MODE — no data will be written[/yellow]")

    # Resolve year range
    current_year = datetime.now(timezone.utc).year
    if start_year and end_year:
        years = list(range(start_year, end_year + 1))
    elif year:
        years = [year]
    else:
        # Default: previous calendar year
        years = [current_year - 1]

    # Resolve sources
    if source == "all":
        sources_to_run = AUTOMATED_SOURCES
    else:
        sources_to_run = [source]

    # Validate manual source requirements
    for s in sources_to_run:
        if s in MANUAL_SOURCES and not file:
            raise click.UsageError(
                f"Source '{s}' requires --file to be specified. "
                f"Example: --source {s} --file /path/to/data.xlsx"
            )

    console.print(f"\n[bold]EWasteTradeFlow Ingestion Pipeline[/bold]")
    console.print(f"Sources: {', '.join(sources_to_run)}")
    console.print(f"Years:   {', '.join(map(str, years))}")
    console.print(f"Dry run: {dry_run}\n")

    results = []
    overall_success = True

    for src in sources_to_run:
        for yr in years:
            console.print(f"[cyan]→ Running {src} for {yr}...[/cyan]")
            success, records_fetched, records_written = _run_source(
                source=src,
                year=yr,
                file_path=file,
                dry_run=dry_run,
                run_type=run_type,
                triggered_by=triggered_by or os.environ.get("USER", "unknown"),
            )
            results.append({
                "source": src,
                "year": yr,
                "status": "✓" if success else "✗",
                "fetched": records_fetched,
                "written": records_written,
            })
            if not success:
                overall_success = False

    _print_results_table(results)

    if not overall_success:
        console.print("\n[red]One or more sources failed. Check logs above.[/red]")
        sys.exit(1)
    else:
        console.print("\n[green]All sources completed successfully.[/green]")


def _run_source(
    source: str,
    year: int,
    file_path: Optional[str],
    dry_run: bool,
    run_type: str,
    triggered_by: str,
) -> tuple[bool, int, int]:
    """
    Run ingestion for a single source+year combination.
    Returns (success, records_fetched, records_written).
    """
    from catalog import start_pipeline_run, complete_pipeline_run

    run_id = None if dry_run else start_pipeline_run(source, run_type, triggered_by)
    records_fetched = 0
    records_written = 0

    try:
        if source == "comtrade":
            records_fetched, records_written = _run_comtrade(year, dry_run)
        elif source == "oecd":
            records_fetched, records_written = _run_oecd(year, dry_run)
        elif source == "wb_governance":
            records_fetched, records_written = _run_wb_governance(year, dry_run)
        elif source == "un_monitor":
            records_fetched, records_written = _run_un_monitor(file_path, year, dry_run)
        elif source == "basel":
            records_fetched, records_written = _run_basel(file_path, dry_run)
        else:
            raise ValueError(f"Unknown source: {source}")

        if run_id:
            complete_pipeline_run(
                run_id,
                status="success",
                records_fetched=records_fetched,
                records_written=records_written,
                s3_prefix=f"raw/{source}/year={year}/",
            )
        return True, records_fetched, records_written

    except Exception as e:
        error_log = traceback.format_exc()
        logger.error("Source '%s' year %d failed: %s", source, year, str(e))

        if run_id:
            complete_pipeline_run(
                run_id,
                status="failed",
                records_fetched=records_fetched,
                records_written=records_written,
                error_log=error_log[:5000],  # truncate to DB column limit
            )
        return False, records_fetched, records_written


def _run_comtrade(year: int, dry_run: bool) -> tuple[int, int]:
    from sources.comtrade import ComtradeClient, normalize, deduplicate
    from upload import upload_dataframe
    import pandas as pd
    import os

    client = ComtradeClient(api_key=os.environ.get("COMTRADE_API_KEY", ""))
    total_fetched = 0
    total_written = 0

    all_batches = []
    for hs_code, batch_df in client.fetch_all_ewaste_codes(year):
        normalized = normalize(batch_df)
        all_batches.append((hs_code, normalized))
        total_fetched += len(batch_df)

    # Deduplicate and upload per HS code
    for hs_code, df in all_batches:
        df = deduplicate(df)
        if len(df) == 0:
            continue
        upload_dataframe(df, source="comtrade", year=year, hs_code=hs_code, dry_run=dry_run)
        total_written += len(df)

    return total_fetched, total_written


def _run_oecd(year: int, dry_run: bool) -> tuple[int, int]:
    from sources.oecd import OecdClient, normalize
    from upload import upload_dataframe

    client = OecdClient()
    df = client.fetch_transboundary_flows(year)
    total_fetched = len(df)
    df = normalize(df)
    if len(df) > 0:
        upload_dataframe(df, source="oecd", year=year, dry_run=dry_run)
    return total_fetched, len(df)


def _run_wb_governance(year: int, dry_run: bool) -> tuple[int, int]:
    from sources.wb_governance import WbGovernanceClient, normalize
    from upload import upload_dataframe

    client = WbGovernanceClient()
    df = client.fetch_governance_indicators(year)
    total_fetched = len(df)
    df = normalize(df)
    if len(df) > 0:
        upload_dataframe(df, source="wb_governance", year=year, dry_run=dry_run)
    return total_fetched, len(df)


def _run_un_monitor(file_path: str, year: int, dry_run: bool) -> tuple[int, int]:
    from sources.un_monitor import parse_excel
    from upload import upload_dataframe

    df = parse_excel(file_path, vintage_year=year)
    total_fetched = len(df)
    if len(df) > 0:
        upload_dataframe(df, source="un_monitor", year=year, dry_run=dry_run)
    return total_fetched, len(df)


def _run_basel(file_path: str, dry_run: bool) -> tuple[int, int]:
    from sources.basel import parse_static
    from upload import upload_dataframe

    df = parse_static(file_path)
    total_fetched = len(df)
    if len(df) > 0:
        upload_dataframe(df, source="basel", year=0, dry_run=dry_run)  # year=0 = static reference
    return total_fetched, len(df)


def _print_results_table(results: list[dict]) -> None:
    table = Table(title="Ingestion Results", show_header=True, header_style="bold cyan")
    table.add_column("Source", style="white")
    table.add_column("Year", style="white")
    table.add_column("Status", style="white")
    table.add_column("Fetched", justify="right")
    table.add_column("Written", justify="right")

    for r in results:
        status_style = "green" if r["status"] == "✓" else "red"
        table.add_row(
            r["source"],
            str(r["year"]),
            f"[{status_style}]{r['status']}[/{status_style}]",
            str(r["fetched"]),
            str(r["written"]),
        )

    console.print(table)


if __name__ == "__main__":
    main()
