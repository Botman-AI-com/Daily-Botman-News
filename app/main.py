import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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

    # Pipeline every N minutes
    scheduler.add_job(
        run_pipeline,
        IntervalTrigger(minutes=settings.fetch_interval_minutes),
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

    # Run once at startup
    logger.info("Running initial pipeline cycle...")
    run_pipeline()

    logger.info(
        "Scheduler started. Pipeline every %d min, cleanup at midnight ART.",
        settings.fetch_interval_minutes,
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
