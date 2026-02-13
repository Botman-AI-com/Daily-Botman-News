import logging
import signal
import sys
from datetime import datetime

from app.cleanup import midnight_cleanup
from app.github_pipeline import run_github_pipeline
from app.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("noticias-botman")


def _run_scheduler() -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    from app.config import settings

    scheduler = BlockingScheduler(timezone="America/Argentina/Buenos_Aires")

    # Pipeline every N minutes, only during operating hours (ART)
    scheduler.add_job(
        run_pipeline,
        CronTrigger(
            hour=(
                f"{settings.schedule_start_hour}"
                f"-{settings.schedule_end_hour - 1}"
            ),
            minute=f"*/{settings.fetch_interval_minutes}",
            timezone="America/Argentina/Buenos_Aires",
        ),
        id="pipeline",
        name="Fetch-Score-Publish Pipeline",
        misfire_grace_time=300,
    )

    # GitHub pipeline every N minutes, same operating hours
    scheduler.add_job(
        run_github_pipeline,
        CronTrigger(
            hour=(
                f"{settings.schedule_start_hour}"
                f"-{settings.schedule_end_hour - 1}"
            ),
            minute=(
                f"*/{settings.github_check_interval_minutes}"
            ),
            timezone="America/Argentina/Buenos_Aires",
        ),
        id="github_pipeline",
        name="GitHub Fetch-Score-Publish Pipeline",
        misfire_grace_time=300,
    )

    # Midnight cleanup
    scheduler.add_job(
        midnight_cleanup,
        CronTrigger(
            hour=0,
            minute=0,
            timezone="America/Argentina/Buenos_Aires",
        ),
        id="cleanup",
        name="Midnight Redis Cleanup",
        misfire_grace_time=600,
    )

    # Run once at startup if within operating hours
    from zoneinfo import ZoneInfo
    now_art = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    in_hours = (
        settings.schedule_start_hour
        <= now_art.hour
        < settings.schedule_end_hour
    )
    if in_hours:
        logger.info("Running initial pipeline cycle...")
        run_pipeline()
        logger.info("Running initial GitHub pipeline cycle...")
        run_github_pipeline()
    else:
        logger.info(
            "Outside operating hours (%d:00–%d:00 ART), skipping initial run.",
            settings.schedule_start_hour,
            settings.schedule_end_hour,
        )

    logger.info(
        "Scheduler started. Pipeline every %d min "
        "(%d:00–%d:00 ART), cleanup at midnight.",
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


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "scheduler"

    if command == "scheduler":
        _run_scheduler()
    elif command == "pipeline":
        run_pipeline()
    elif command == "github":
        run_github_pipeline()
    elif command == "cleanup":
        midnight_cleanup()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python -m app.main [scheduler|pipeline|github|cleanup]")
        sys.exit(1)


if __name__ == "__main__":
    main()
