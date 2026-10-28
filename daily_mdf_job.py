
import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "daily_mdf_job.log"


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def run_script(script_name, extra_args=None):
    script_path = BASE_DIR / script_name

    if not script_path.exists():
        logging.error("Script not found: %s", script_path)
        return False

    command = [sys.executable, str(script_path)]

    if extra_args:
        command.extend(extra_args)

    logging.info("Starting: %s", " ".join(command))

    try:
        result = subprocess.run(
            command,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=24 * 60 * 60,
            check=False,
        )

        if result.stdout:
            logging.info("%s output:\n%s", script_name, result.stdout)

        if result.stderr:
            logging.warning("%s errors/output:\n%s", script_name, result.stderr)

        if result.returncode != 0:
            logging.error(
                "%s failed with exit code %s",
                script_name,
                result.returncode,
            )
            return False

        logging.info("%s completed successfully", script_name)
        return True

    except subprocess.TimeoutExpired:
        logging.error("%s timed out", script_name)
        return False
    except Exception:
        logging.exception("Unexpected error running %s", script_name)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Daily Itsybitsy MDF product collection job"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit product collection for testing, e.g. --limit 5",
    )
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    setup_logging()

    logging.info("=" * 60)
    logging.info("DAILY MDF JOB STARTED: %s", datetime.now().isoformat())
    logging.info("=" * 60)

    # Step 1: Discover the latest MDF product URLs.
    if not run_script("collect_mdf_urls.py"):
        logging.error("Daily MDF job stopped: URL collection failed")
        sys.exit(1)

    # Step 2: Collect product details and save them to SQL Server.
    collector_args = ["--refresh"]

    if args.limit is not None:
        collector_args.extend(["--limit", str(args.limit)])

    if not run_script("multi_product_collector.py", collector_args):
        logging.error("Daily MDF job finished with errors")
        sys.exit(1)

    logging.info("DAILY MDF JOB COMPLETED SUCCESSFULLY")
    logging.info("Log file: %s", LOG_FILE)


if __name__ == "__main__":
    main()
