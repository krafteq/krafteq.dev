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
                resolved = info["url"]
                log.info(f"Resolved YouTube URL to direct stream")
                return resolved
        except Exception as e:
            log.error(f"Failed to resolve YouTube URL: {e}")
    return url


class CameraDetector:
    def __init__(self, camera: dict):
        self.camera = camera
        self.name   = camera["name"]
        self.source = (
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

        log.info(f"[{self.name}] Initializing...")
        threading.Thread(target=self._llm_worker, daemon=True).start()

    def _llm_worker(self):
        while True:
            frame = self.llm_queue.get()
            if frame is None:
                break
            try:
                log.info(f"[{self.name}] LLM worker received frame, sending to {os.getenv('LLM_PROVIDER', 'ollama')}...")

                self.last_desc = {
                    "objects": self._ask(frame,
                        "List only the physical objects you see. Comma separated, no sentences."),
                    "people":  self._ask(frame,
                        "Describe the people in this image briefly (count, appearance). If none, say 'none'."),
                    "actions": self._ask(frame,
                        "What actions or activities are happening? Comma separated, no sentences."),
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
            log.info(f"[{self.name}] Asking: '{prompt[:40]}...'")
            result = self.provider.ask(frame, prompt)
            log.info(f"[{self.name}] Response: '{result[:80]}'")
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
        cv2.putText(frame, self.name, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y = 60
        for label, key in [("Objects", "objects"), ("People", "people"), ("Actions", "actions")]:
            val = self.last_desc.get(key)
            if val:
                cv2.putText(frame, f"{label}: {val[:60]}", (10, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                y += 25

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

                    log.info(f"[{self.name}] Sending frame to {os.getenv('LLM_PROVIDER', 'ollama')} ({os.getenv('LLM_MODEL', 'moondream')})...")
                    self._analyze_async(frame)

                if not HEADLESS:
                    display = frame.copy()
                    self._draw_overlay(display)
                    cv2.imshow(f"Detector — {self.name}", display)
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