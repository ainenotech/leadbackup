"""Render Keep-Alive Background Daemon for Nenotechnology Outreach Backend.

Render's free tier automatically spins down web services after 15 minutes of inactivity.
This daemon runs in a background thread inside FastAPI and dispatches a lightweight
HTTP GET request to its own public URL (/api/health) every 9 minutes (540 seconds).
Because this outbound request travels through Render's public edge router back to the container,
Render records active inbound traffic and resets the 15-minute inactivity countdown,
keeping the API and background workers awake 24/7.
"""

import logging
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("render_keepalive")


class RenderKeepAliveDaemon:
    """Thread-safe background daemon that sends periodic keep-alive HTTP pings
    to the server's public URL to prevent Render from going idle/sleeping.
    """

    _thread: Optional[threading.Thread] = None
    _stop_event: threading.Event = threading.Event()
    _is_running: bool = False

    # Metrics
    _total_pings: int = 0
    _successful_pings: int = 0
    _failed_pings: int = 0
    _last_ping_time: Optional[datetime] = None
    _last_latency_ms: float = 0.0
    _last_status_code: Optional[int] = None
    _last_error: Optional[str] = None
    _target_url: str = ""

    @classmethod
    def resolve_target_url(cls) -> str:
        """Determines the public endpoint to ping.
        Prioritizes RENDER_EXTERNAL_URL (auto-injected by Render),
        then API_BASE_URL (.env), then localhost fallback.
        """
        raw_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("API_BASE_URL") or "http://127.0.0.1:8000"
        clean = raw_url.rstrip("/")
        if not clean.endswith("/api/health") and not clean.endswith("/health"):
            target = f"{clean}/api/health"
        else:
            target = clean
        return target

    @classmethod
    def ping_now(cls, timeout: int = 15) -> Dict[str, Any]:
        """Executes a single keepalive ping immediately and records telemetry."""
        target = cls._target_url or cls.resolve_target_url()
        cls._total_pings += 1
        cls._last_ping_time = datetime.now(timezone.utc)

        start_time = time.time()
        try:
            req = urllib.request.Request(
                target,
                headers={"User-Agent": "RenderKeepAliveDaemon/1.0 (HealthCheck)"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status = response.status
                latency = round((time.time() - start_time) * 1000, 2)
                cls._last_latency_ms = latency
                cls._last_status_code = status
                cls._last_error = None
                cls._successful_pings += 1
                logger.info(f"[KeepAlive] ✅ Ping successful to {target} ({status} - {latency}ms)")
                return {
                    "success": True,
                    "target": target,
                    "status_code": status,
                    "latency_ms": latency,
                    "timestamp": cls._last_ping_time.isoformat(),
                }
        except Exception as e:
            # Fallback to root endpoint "/" if /api/health returned 404 (e.g. pending redeploy)
            if getattr(e, "code", None) == 404 and "/api/health" in target:
                root_fallback = target.replace("/api/health", "/")
                try:
                    req_fb = urllib.request.Request(
                        root_fallback,
                        headers={"User-Agent": "RenderKeepAliveDaemon/1.0 (Fallback)"},
                        method="GET",
                    )
                    with urllib.request.urlopen(req_fb, timeout=timeout) as fb_resp:
                        status = fb_resp.status
                        latency = round((time.time() - start_time) * 1000, 2)
                        cls._last_latency_ms = latency
                        cls._last_status_code = status
                        cls._last_error = None
                        cls._successful_pings += 1
                        logger.info(f"[KeepAlive] ✅ Ping successful to fallback {root_fallback} ({status} - {latency}ms)")
                        return {
                            "success": True,
                            "target": root_fallback,
                            "status_code": status,
                            "latency_ms": latency,
                            "timestamp": cls._last_ping_time.isoformat(),
                            "note": "Fell back to root URL",
                        }
                except Exception:
                    pass

            latency = round((time.time() - start_time) * 1000, 2)
            cls._last_latency_ms = latency
            cls._last_status_code = getattr(e, "code", 0) or 500
            cls._last_error = str(e)
            cls._failed_pings += 1
            logger.warning(f"[KeepAlive] ⚠️ Ping failed to {target}: {e} ({latency}ms)")
            return {
                "success": False,
                "target": target,
                "error": str(e),
                "latency_ms": latency,
                "timestamp": cls._last_ping_time.isoformat(),
            }

    @classmethod
    def start(cls, interval_minutes: Optional[int] = None) -> None:
        """Starts the background keepalive daemon loop."""
        if cls.is_running():
            return

        # Default interval: 9 minutes (540 seconds)
        # Render idle timeout is 15 minutes, so 9 minutes guarantees the instance stays awake.
        interval_min = interval_minutes or int(os.getenv("KEEPALIVE_INTERVAL_MINUTES", "9"))
        interval_secs = max(60, interval_min * 60)

        cls._target_url = cls.resolve_target_url()
        cls._stop_event.clear()
        cls._is_running = True

        def _loop():
            logger.info(
                f"[KeepAlive] 🚀 Render KeepAlive Daemon started. Pinging {cls._target_url} every {interval_min}m."
            )
            # Wait 30 seconds after server boot before firing first ping
            if cls._stop_event.wait(30):
                return
            cls.ping_now()

            while not cls._stop_event.is_set():
                if cls._stop_event.wait(interval_secs):
                    break
                cls.ping_now()

            cls._is_running = False
            logger.info("[KeepAlive] 🛑 Render KeepAlive Daemon stopped.")

        cls._thread = threading.Thread(
            target=_loop,
            name="RenderKeepAliveDaemonThread",
            daemon=True,
        )
        cls._thread.start()

    @classmethod
    def stop(cls) -> None:
        """Signals the keepalive daemon to stop."""
        cls._stop_event.set()
        cls._is_running = False

    @classmethod
    def is_running(cls) -> bool:
        return cls._is_running and cls._thread is not None and cls._thread.is_alive()

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Returns comprehensive diagnostic stats for the /api/health endpoint."""
        return {
            "is_running": cls.is_running(),
            "target_url": cls._target_url or cls.resolve_target_url(),
            "total_pings": cls._total_pings,
            "successful_pings": cls._successful_pings,
            "failed_pings": cls._failed_pings,
            "last_ping_time": cls._last_ping_time.isoformat() if cls._last_ping_time else None,
            "last_latency_ms": cls._last_latency_ms,
            "last_status_code": cls._last_status_code,
            "last_error": cls._last_error,
        }
