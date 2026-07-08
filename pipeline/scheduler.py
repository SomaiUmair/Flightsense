"""Run ingestion automatically on a fixed interval using APScheduler.

A price tracker needs to collect repeatedly and unattended; this schedules the
ingest job so history builds over time.
"""

from apscheduler.schedulers.blocking import BlockingScheduler

from pipeline.collectors.ingest import ingest

# Kept short for visibility; in real use this would be hours, not minutes.
INTERVAL_MINUTES = 30


def main() -> None:
    """Start the scheduler: collect once now, then every INTERVAL_MINUTES."""
    # BlockingScheduler runs in the foreground and keeps the process alive.
    scheduler = BlockingScheduler()
    scheduler.add_job(ingest, "interval", minutes=INTERVAL_MINUTES, id="ingest_prices")

    print(
        f"Scheduler started — collecting now, then every {INTERVAL_MINUTES} min. "
        "Press Ctrl+C to stop."
    )
    ingest()  # collect once immediately rather than waiting a full interval

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nScheduler stopped.")


if __name__ == "__main__":
    main()
