import argparse
import logging
import subprocess
import sys
from pathlib import Path
import time

BASE_DIR = Path(__file__).resolve().parent
URL_FILE = BASE_DIR / "mdf_product_urls.txt"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "collector.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

def main():
    parser = argparse.ArgumentParser(
    description="Collect multiple Itsybitsy product records"
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch fresh product pages instead of using cached HTML"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of products to process"
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    if not URL_FILE.exists():
        print(f"URL file not found: {URL_FILE}")
        return 1

    urls = [
        line.strip()
        for line in URL_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not urls:
        print("No product URLs found in product_urls.txt")
        return 1
    
    if args.limit is not None:
        urls = urls[:args.limit]

    succeeded = 0
    failed = 0

    print(f"Starting collection for {len(urls)} product URL(s)...")

    for index, url in enumerate(urls, start=1):
        print(f"\n[{index}/{len(urls)}] Processing: {url}")
        command = [
            sys.executable,
            str(BASE_DIR / "save_product.py"),
            "--url",
            url,
        ]

        if args.refresh:
            command.append("--refresh")

        try:
            result = subprocess.run(
                command,
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300
            )

            if result.stdout:
                print(result.stdout)

            if result.stderr:
                print(result.stderr)

            if result.returncode == 0:
                succeeded += 1
                logging.info("SUCCESS | %s", url)
                print("Result: SUCCESS")
            else:
                failed += 1
                logging.error(
                    "FAILED | %s | %s",
                    url,
                    result.stderr[-3000:]
                )
                print("Result: FAILED")
                if result.stderr:
                    print(result.stderr[-3000:])

        except subprocess.TimeoutExpired:
            failed += 1
            logging.error("TIMEOUT | %s", url)
            print("Result: TIMEOUT")

        except Exception:
            failed += 1
            logging.exception("ERROR | %s", url)
            print("Result: ERROR. Check logs/collector.log")
        
        finally:
            # Be polite to the website between products.
            time.sleep(5)

    print("\n--- COLLECTION SUMMARY ---")
    print(f"Total URLs: {len(urls)}")
    print(f"Succeeded: {succeeded}")
    print(f"Failed: {failed}")
    print(f"Log file: {LOG_DIR / 'collector.log'}")
    time.sleep(3)

    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())