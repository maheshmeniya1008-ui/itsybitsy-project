"""
Run Itsybitsy Product API with Cloudflare Live Public Tunnel
This makes your API accessible to anyone across the internet over HTTPS.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CLOUDFLARED = BASE_DIR / "cloudflared.exe"
PORT = int(os.getenv("PORT", 8000))
SECURITY_KEY = os.getenv("API_SECURITY_KEY", "itsybitsy_secret_token_2026")


def main():
    print("=" * 60)
    print("  🛍️  Starting Itsybitsy Live API & Cloudflare Tunnel")
    print("=" * 60)
    print(f"Local Port:    {PORT}")
    print(f"Security Key:  {SECURITY_KEY}")
    print("=" * 60)

    if not CLOUDFLARED.exists():
        print(f"Error: {CLOUDFLARED} not found.")
        sys.exit(1)

    # 1. Start Cloudflare Tunnel
    cmd = [str(CLOUDFLARED), "tunnel", "--url", f"http://127.0.0.1:{PORT}"]
    print(f"Launching tunnel: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    import re

    tunnel_url = None
    start_time = time.time()

    while time.time() - start_time < 30:
        line = process.stdout.readline()
        if not line:
            break
        # Match URL pattern like https://subdomain.trycloudflare.com
        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match:
            tunnel_url = match.group(0)
            break

    if tunnel_url:
        print("\n" + "=" * 60)
        print("  🎉 LIVE PUBLIC API IS READY!")
        print("=" * 60)
        print(f"Live Base URL:\n  {tunnel_url}\n")
        print("Live Category Endpoint (mdf-collection):")
        print(f"  {tunnel_url}/itsy_bitsyAPI/{SECURITY_KEY}/products/category/mdf-collection\n")
        print("Live Categories Endpoint:")
        print(f"  {tunnel_url}/itsy_bitsyAPI/{SECURITY_KEY}/products/categories\n")
        print("=" * 60)
        print("Press Ctrl+C to stop the tunnel.\n")
    else:
        print("Warning: Could not automatically parse tunnel URL. Check cloudflared output.")

    try:
        while True:
            line = process.stdout.readline()
            if not line:
                break
    except KeyboardInterrupt:
        print("\nStopping live tunnel...")
        process.terminate()


if __name__ == "__main__":
    main()
