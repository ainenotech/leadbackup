"""Standalone Render Keep-Alive Worker CLI.

Keeps Render free-tier web services awake 24/7 by dispatching periodic health-check
pings. Can be run locally, in background, or as a system service.

Usage:
    python keepalive_worker.py                     # Runs continuous pinger every 9m
    python keepalive_worker.py --interval 300      # Runs pinger every 5m
    python keepalive_worker.py --once              # Executes single ping & exits
    python keepalive_worker.py --url http://...    # Custom target URL
"""

import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()

DEFAULT_URL = os.getenv("API_BASE_URL", "https://neno-lead.onrender.com").rstrip("/")
if not DEFAULT_URL.endswith("/api/health") and not DEFAULT_URL.endswith("/health"):
    DEFAULT_URL = f"{DEFAULT_URL}/api/health"


def ping(url: str, timeout: int = 30) -> bool:
    start = time.time()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "StandaloneKeepAliveWorker/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency_ms = round((time.time() - start) * 1000, 1)
            status = response.status
            print(f"[{now_str}] ✅ PING SUCCESS -> {url} [HTTP {status}] ({latency_ms}ms)")
            return True
    except urllib.error.HTTPError as e:
        latency_ms = round((time.time() - start) * 1000, 1)
        if e.code == 404 and "/api/health" in url:
            root_fallback = url.replace("/api/health", "/")
            print(f"[{now_str}] ℹ️  /api/health returned 404 (pending deploy). Retrying root endpoint {root_fallback}...")
            return ping(root_fallback, timeout=timeout)
        print(f"[{now_str}] ⚠️ HTTP ERROR {e.code} -> {url} ({latency_ms}ms)")
        return False
    except Exception as e:
        latency_ms = round((time.time() - start) * 1000, 1)
        print(f"[{now_str}] ❌ CONNECTION ERROR -> {url}: {e} ({latency_ms}ms)")
        return False


def main():
    parser = argparse.ArgumentParser(description="Render 24/7 Keep-Alive Worker")
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Target health URL to ping (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=540,
        help="Ping interval in seconds (default: 540s = 9 minutes)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single ping pass and exit immediately",
    )
    args = parser.parse_args()

    print("=" * 65)
    print(" 🚀 AINeotechnology — Render 24/7 Keep-Alive Service")
    print(f" Target:   {args.url}")
    print(f" Interval: {args.interval} seconds ({round(args.interval / 60, 1)} minutes)")
    print("=" * 65)

    if args.once:
        success = ping(args.url)
        sys.exit(0 if success else 1)

    # Initial ping
    ping(args.url)

    while True:
        try:
            time.sleep(args.interval)
            ping(args.url)
        except KeyboardInterrupt:
            print("\n[KeepAlive Worker] Stopped by user.")
            break


if __name__ == "__main__":
    main()
