"""Run the ingestion pipeline automatically on a schedule.

Running ingest by hand is fine for testing, but a price *tracker* needs to
collect prices repeatedly, unattended, so history builds up over time. This
uses APScheduler to call ingest() on a fixed interval.

Run with:
    python -m pipeline.scheduler
Stop with Ctrl+C.
"""

from apscheduler.schedulers.blocking import BlockingScheduler

from pipeline.collectors.ingest import ingest

# How often to collect prices. Kept short so you can watch it work; in real use
# you'd track prices every few hours (e.g. hours=6), not every few minutes.
INTERVAL_MINUTES = 30


def main() -> None:
    # BlockingScheduler runs in the foreground and keeps the process alive on
    # its own -- the right choice for a standalone script whose only job is to
    # sit there and fire the ingestion on schedule.
    scheduler = BlockingScheduler()

    # Register ingest() to run every INTERVAL_MINUTES. `id` names the job so it
    # can't be accidentally added twice.
    scheduler.add_job(ingest, "interval", minutes=INTERVAL_MINUTES, id="ingest_prices")

    print(
        f"Scheduler started — collecting now, then every {INTERVAL_MINUTES} min. "
        "Press Ctrl+C to stop."
    )

    # Collect once immediately so we don't wait a full interval for the first
    # batch of prices.
    ingest()

    try:
        # start() blocks here, waking up to run the job on schedule.
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        # Ctrl+C is the normal way to stop this script -- handle it cleanly
        # instead of dumping a traceback.
        print("\nScheduler stopped.")


if __name__ == "__main__":
    main()
