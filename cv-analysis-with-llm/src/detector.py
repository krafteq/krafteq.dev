import cv2
import os
import time
import threading
import logging
from collections import deque
from queue import Queue
from datetime import datetime
from config import cfg
from notifier import Notifier
from event_logger import EventLogger
from llm_provider import get_provider

HEADLESS    = os.getenv("HEADLESS", "false").lower() == "true"
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

log = logging.getLogger(__name__)


def _resolve_stream_url(url: str) -> str:
    """Resolve YouTube or other stream URLs to a direct playable URL."""
    if "youtube.com" in url or "youtu.be" in url:
        try:
            import yt_dlp
            ydl_opts = {"quiet": True, "format": "best[ext=mp4]/best"}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                log.info("Resolved YouTube URL to direct stream")
                return info["url"]
        except Exception as e:
            log.error(f"Failed to resolve YouTube URL: {e}")
    return url


def _build_prompts(camera: dict, events: list[dict]) -> dict:
    """
    Build context-aware prompts using:
    - camera context: sets the scene for all prompts
    - event context: adds focused instruction per field based on active events
    """
    cam_ctx = camera.get("context", "a security camera")

    # Collect extra context per field from event definitions
    field_hints = {"objects": [], "people": [], "actions": []}
    for event in events:
        event_ctx = event.get("context", "")
        if event_ctx:
            for field in event.get("match_in", []):
                if field in field_hints:
                    field_hints[field].append(event_ctx)

    def build(field: str, instruction: str) -> str:
        hints = " ".join(set(field_hints[field]))  # deduplicate
        hint_str = f" Additionally: {hints}" if hints else ""
        return (
            f"You are analysing {cam_ctx}. "
            f"{instruction}{hint_str} "
            f"Be concise — comma separated, no full sentences."
        )

    return {
        "objects": build("objects", "List only the key physical objects visible."),
        "people":  build("people",  "Describe visible people — count and appearance. If none, say 'none'."),
        "actions": build("actions", "Describe the main activities or actions happening."),
    }


class CameraDetector:
    def __init__(self, camera: dict):
        self.name    = camera["name"]
        self.prompts = _build_prompts(camera, cfg.events)
        self.source  = (
            camera["device_index"] if camera["type"] == "usb"
            else _resolve_stream_url(camera["url"]) if camera["type"] == "stream"
            else f"rtsp://{camera['user']}:{camera['password']}@{camera['ip']}:{camera['port']}/{camera['stream']}"
        )

        self.llm_queue      = Queue(maxsize=1)
        self.last_desc      = {"objects": None, "people": None, "actions": None}
        self.frame_buffer   = deque(maxlen=cfg.buffer_seconds * cfg.fps)
        self._running       = False
        self._last_analysis = 0
        self._last_response = 0
        self.notifier       = Notifier()
        self.event_logger   = EventLogger(cfg.events)
        self.provider       = get_provider()

        log.info(f"[{self.name}] Initializing | context: {camera.get('context', 'none')[:60]}")
        threading.Thread(target=self._llm_worker, daemon=True).start()

    def _llm_worker(self):
        while True:
            frame = self.llm_queue.get()
            if frame is None:
                break
            try:
                self.last_desc = {
                    "objects": self._ask(frame, self.prompts["objects"]),
                    "people":  self._ask(frame, self.prompts["people"]),
                    "actions": self._ask(frame, self.prompts["actions"]),
                }
                self._last_response = time.time()

                ts = datetime.now().strftime("%H:%M:%S")
                log.info(f"[{self.name}] [{ts}] "
                         f"Objects: {self.last_desc['objects']} | "
                         f"People: {self.last_desc['people']} | "
                         f"Actions: {self.last_desc['actions']}")

                matched_tags = self.event_logger.log_events(self.name, self.last_desc)
                notify_events = [
                    e for e in cfg.events
                    if e.get("tag") in matched_tags and e.get("notify", False)
                ]
                if notify_events:
                    self.notifier.notify(self.name, self.last_desc)

            except Exception as e:
                log.exception(f"[{self.name}] LLM error: {e}")

    def _ask(self, frame, prompt: str) -> str:
        try:
            result = self.provider.ask(frame, prompt)
            log.info(f"[{self.name}] → {result[:80]}")
            return result
        except Exception as e:
            log.error(f"[{self.name}] Provider error: {e}")
            return ""

    def _analyze_async(self, frame):
        if self.llm_queue.empty():
            try:
                self.llm_queue.put_nowait(frame.copy())
            except Exception:
                pass

    def _draw_overlay(self, frame):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

        cv2.putText(frame, self.name, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        y = 50
        for label, key, color in [
            ("Objects", "objects", (200, 200, 200)),
            ("People",  "people",  (100, 255, 100)),
            ("Actions", "actions", (100, 200, 255)),
        ]:
            val = self.last_desc.get(key)
            if val:
                cv2.putText(frame, f"{label}: {val[:70]}", (10, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
                y += 22

    def _open_stream(self):
        cap = cv2.VideoCapture(self.source)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            raise ConnectionError(f"[{self.name}] Could not open: {self.source}")
        return cap

    def run(self):
        try:
            cap = self._open_stream()
        except ConnectionError as e:
            log.error(e)
            return

        log.info(f"[{self.name}] Stream opened! Press 'q' to quit")
        self._running = True
        interval      = int(os.getenv("ANALYSIS_INTERVAL", "10"))

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    log.warning(f"[{self.name}] Frame grab failed, reconnecting...")
                    cap.release()
                    try:
                        cap = self._open_stream()
                    except ConnectionError as e:
                        log.error(e)
                        break
                    continue

                self.frame_buffer.append(frame)

                now = time.time()
                if now - self._last_analysis >= interval:
                    self._last_analysis = now
                    if self._last_response > 0 and (now - self._last_response) > LLM_TIMEOUT:
                        log.warning(f"[{self.name}] LLM timeout — no response in {LLM_TIMEOUT}s")
                        self.event_logger.log_timeout(self.name)
                    self._analyze_async(frame)

                if not HEADLESS:
                    display = frame.copy()
                    self._draw_overlay(display)
                    cv2.imshow(f"{self.name} — Live", display)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self._running = False

        except KeyboardInterrupt:
            log.info(f"[{self.name}] Interrupted")

        finally:
            self.llm_queue.put(None)
            self.event_logger.close()
            cap.release()
            if not HEADLESS:
                cv2.destroyAllWindows()
            log.info(f"[{self.name}] Stopped cleanly")