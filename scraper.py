from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
ARCHIVE_DIR = BASE_DIR / "data" / "product_pages"

PRODUCT_URL = (
    "https://itsybitsy.in/collections/"
    "top-hero-products/products/"
    "decor-varnish-gloss100-ml"
)

def create_http_session():
    retry_strategy = Retry(
        total=5,
        connect=3,
        read=3,
        status=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
        raise_on_status=True,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)

    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "User-Agent": "ItsybitsyProductCollector/1.0"
    })

    return session

def find_product_json(data):
    if isinstance(data, list):
        for item in data:
            result = find_product_json(item)
            if result:
                return result

    elif isinstance(data, dict):
        product_type = data.get("@type", [])

        if isinstance(product_type, str):
            product_type = [product_type]

        if "Product" in product_type:
            return data

        for value in data.values():
            if isinstance(value, (dict, list)):
                result = find_product_json(value)
                if result:
                    return result

    return None


def find_saved_page(url):
    """Find the newest archived copy of this exact URL."""
    if not ARCHIVE_DIR.exists():
        return None

    metadata_files = ARCHIVE_DIR.glob(
        "*/*.meta.json"
    )

    matches = []

    for metadata_file in metadata_files:
        try:
            metadata = json.loads(
                metadata_file.read_text(encoding="utf-8")
            )

            if metadata.get("url") != url:
                continue

            html_path = metadata_file.parent / metadata["html_file"]

            if html_path.is_file():
                matches.append(
                    (metadata.get("fetched_at", ""), html_path)
                )

        except (OSError, ValueError, KeyError):
            continue

    if not matches:
        return None

    # ISO timestamps sort chronologically.
    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1]


def extract_from_html(html, url):
    soup = BeautifulSoup(html, "html.parser")
    product = None

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):
        try:
            data = json.loads(
                script.string or script.get_text()
            )
            product = find_product_json(data)

            if product:
                break

        except (json.JSONDecodeError, TypeError):
            continue

    if not product:
        raise ValueError(
            "Product JSON-LD not found in saved HTML."
        )

    offers = product.get("offers", {})

    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    if not isinstance(offers, dict):
        offers = {}

    price_value = offers.get("price")

    if price_value is None:
        price_value = offers.get("lowPrice")

    try:
        price_value = (
            float(price_value)
            if price_value is not None
            else None
        )
    except (ValueError, TypeError):
        price_value = None

    brand = product.get("brand")

    if isinstance(brand, dict):
        brand = brand.get("name")
    elif not isinstance(brand, str):
        brand = None

    # Avoid saving suspicious internal metadata as a brand.
    if brand and re.search(r"\bS\d+\s+Z\d+\b", brand):
        brand = None

    availability_url = str(
        offers.get("availability", "")
    )

    sku = product.get("sku") or product.get("productID")
    product_slug = urlparse(url).path.rstrip("/").split("/")[-1]

    category = product.get("category")
    if not category:
        cat_match = re.search(r"/collections/([^/]+)/products/", url)
        if cat_match:
            category = cat_match.group(1).replace("-", " ").title()

    return {
        "source_product_id": str(sku or product_slug),
        "product_name": product.get("name"),
        "brand": brand,
        "category": category,
        "sku": sku,
        "regular_price": None,
        "promotional_price": price_value,
        "currency": offers.get("priceCurrency", "INR"),
        "availability": availability_url.rsplit("/", 1)[-1]
        or "Unknown",
        "product_url": url
    }


def extract_product(url, refresh=False):
    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname != "itsybitsy.in"
    ):
        raise ValueError(
            "Only HTTPS URLs from itsybitsy.in are allowed."
        )

    # 1. Reuse the archive unless a refresh is requested.
    if not refresh:
        saved_path = find_saved_page(url)

        if saved_path:
            print(f"Reading saved HTML: {saved_path}")

            html = saved_path.read_text(
                encoding="utf-8"
            )

            return extract_from_html(html, url)

    # 2. Fetch only when there is no archive or refresh=True.
    print("Fetching product page from website...")

    """response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; "
                "ProductDataResearch/1.0)"
            ),
            "Accept": "text/html"
        },
        timeout=20
    )"""
    
    session = create_http_session()
    response = session.get(url, timeout=30)
    response.raise_for_status()
    html = response.text

    # Extract first so we can use the product ID in filenames.
    product_data = extract_from_html(html, url)

    product_id = re.sub(
        r"[^A-Za-z0-9_-]",
        "_",
        product_data["source_product_id"]
    )

    # Folder format: YYYY_MM_DD_HH
    folder_name = datetime.now().strftime("%Y_%m_%d_%H")
    target_dir = ARCHIVE_DIR / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    html_filename = f"{product_id}.html"
    html_path = target_dir / html_filename

    metadata_path = target_dir / f"{product_id}.meta.json"

    # Save original page HTML.
    html_path.write_text(
        html,
        encoding="utf-8"
    )

    metadata = {
        "url": url,
        "source_product_id": product_data["source_product_id"],
        "fetched_at": datetime.now().astimezone().isoformat(),
        "html_file": html_filename
    }

    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Archived HTML: {html_path}")

    return product_data


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv

    try:
        result = extract_product(
            PRODUCT_URL,
            refresh=refresh
        )

        print("\n--- EXTRACTED PRODUCT DATA ---")
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception as error:
        print("Product extraction failed:", error)
