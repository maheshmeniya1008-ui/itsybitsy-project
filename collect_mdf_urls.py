import json
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent

COLLECTION_URL = "https://itsybitsy.in/collections/mdf-collection"
OUTPUT_FILE = BASE_DIR / "mdf_product_urls.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ProductResearchBot/1.0)",
    "Accept": "text/html",
}

def normalize_url(url):
    url = urldefrag(url)[0]
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return None

    if parsed.hostname not in ("itsybitsy.in", "www.itsybitsy.in"):
        return None

    # Remove query strings and fragments from product URLs.
    return f"https://itsybitsy.in{parsed.path}".rstrip("/")

def get_page(session, url):
    response = session.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    if "text/html" not in response.headers.get("Content-Type", ""):
        raise ValueError(f"Unexpected content type for {url}")

    return response.text

def collect_product_urls():
    session = requests.Session()
    pending_pages = [COLLECTION_URL]
    visited_pages = set()
    product_urls = set()

    while pending_pages:
        page_url = pending_pages.pop(0)

        if page_url in visited_pages:
            continue

        visited_pages.add(page_url)
        print(f"Reading collection page: {page_url}")

        html = get_page(session, page_url)
        soup = BeautifulSoup(html, "html.parser")

        # Product links normally contain /products/ in their URL.
        for anchor in soup.select('a[href*="/products/"]'):
            href = anchor.get("href")
            if not href:
                continue

            full_url = normalize_url(urljoin(page_url, href))
            if not full_url:
                continue

            path = urlparse(full_url).path
            if "/products/" not in path:
                continue

            product_urls.add(full_url)

        # Follow pagination links belonging to this collection.
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "")
            next_url = urljoin(page_url, href)
            parsed = urlparse(next_url)

            if parsed.hostname not in ("itsybitsy.in", "www.itsybitsy.in"):
                continue

            if parsed.path.rstrip("/") != urlparse(COLLECTION_URL).path.rstrip("/"):
                continue

            query = parsed.query.lower()
            if "page=" in query:
                clean_page_url = (
                    f"https://itsybitsy.in{parsed.path}?{parsed.query}"
                )
                if clean_page_url not in visited_pages:
                    pending_pages.append(clean_page_url)

        print(f"Unique product URLs found so far: {len(product_urls)}")
        time.sleep(1)

    sorted_urls = sorted(product_urls)

    OUTPUT_FILE.write_text(
        "\n".join(sorted_urls) + ("\n" if sorted_urls else ""),
        encoding="utf-8",
    )

    print("\n--- MDF URL COLLECTION SUMMARY ---")
    print(f"Collection pages visited: {len(visited_pages)}")
    print(f"Unique product URLs: {len(sorted_urls)}")
    print(f"Saved to: {OUTPUT_FILE}")

    if not sorted_urls:
        print(
            "WARNING: No product URLs found. Check the website HTML, "
            "pagination, and robots/website access rules."
        )

if __name__ == "__main__":
    try:
        collect_product_urls()
    except Exception as error:
        print(f"URL collection failed: {error}")
        raise