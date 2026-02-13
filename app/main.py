import logging
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.cleanup import midnight_cleanup
from app.config import settings
from app.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("noticias-botman")


def main() -> None:
    scheduler = BlockingScheduler(timezone="America/Argentina/Buenos_Aires")

    # Pipeline every N minutes, only during operating hours (ART)
    scheduler.add_job(
        run_pipeline,
        CronTrigger(
            hour=f"{settings.schedule_start_hour}-{settings.schedule_end_hour - 1}",
            minute=f"*/{settings.fetch_interval_minutes}",
            timezone="America/Argentina/Buenos_Aires",
        ),
        id="pipeline",
        name="Fetch-Score-Publish Pipeline",
        misfire_grace_time=300,
    )

    # Midnight cleanup
    scheduler.add_job(
        midnight_cleanup,
        CronTrigger(hour=0, minute=0, timezone="America/Argentina/Buenos_Aires"),
        id="cleanup",
        name="Midnight Redis Cleanup",
        misfire_grace_time=600,
    )

    # Run once at startup if within operating hours
    from zoneinfo import ZoneInfo
    now_art = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    if settings.schedule_start_hour <= now_art.hour < settings.schedule_end_hour:
        logger.info("Running initial pipeline cycle...")
        run_pipeline()
    else:
        logger.info(
            "Outside operating hours (%d:00–%d:00 ART), skipping initial run.",
            settings.schedule_start_hour,
            settings.schedule_end_hour,
        )

    logger.info(
        "Scheduler started. Pipeline every %d min (%d:00–%d:00 ART), cleanup at midnight ART.",
        settings.fetch_interval_minutes,
        settings.schedule_start_hour,
        settings.schedule_end_hour,
    )

    def shutdown(signum, frame):
        logger.info("Shutting down...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    scheduler.start()


if __name__ == "__main__":
    main()
