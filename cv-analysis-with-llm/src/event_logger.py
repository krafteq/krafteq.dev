import logging
import json
import os
from datetime import datetime

log = logging.getLogger(__name__)

EVENTS_LOG_FILE = os.getenv("EVENTS_LOG_FILE", "logs/events.log")


def _as_text(value) -> str:
    """Coerce an observation field to a searchable string.
    Handles None, strings, and lists/tuples e.g. ['person', 'car']."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return " ".join(_as_text(v) for v in value)
    return str(value)


class EventLogger:
    def __init__(self, events_config: list[dict]):
        """
        events_config: list of event defs loaded from vision_config.yaml
        Each event:
            tag:        str  — label used in logs e.g. PERSON_DETECTED
            keywords:   list — words to match
            match_in:   list — which fields to search: objects | people | actions
            notify:     bool — whether to also trigger a notification
        """
        self.events = events_config or []

        # Tags whose event has notify: true — used to flag log entries.
        self._notify_tags = {
            e.get("tag") for e in self.events if e.get("notify", False)
        }

        if not self.events:
            log.warning("No events defined in vision_config.yaml — event logging disabled")
        else:
            log.info(f"Event logger ready — tracking {len(self.events)} event types")

        os.makedirs(os.path.dirname(EVENTS_LOG_FILE), exist_ok=True)
        self._file = open(EVENTS_LOG_FILE, "a", encoding="utf-8")

    def match(self, camera_name: str, observation: dict) -> list[str]:
        """Check observation against all event definitions, return matched tags."""
        matched_tags = []

        for event in self.events:
            tag      = event.get("tag", "UNKNOWN")
            keywords = [k.lower() for k in event.get("keywords", [])]
            fields   = event.get("match_in", ["objects", "people", "actions"])

            search_text = " ".join(
                _as_text(observation.get(f)) for f in fields
            ).lower()

            if any(kw in search_text for kw in keywords):
                matched_tags.append(tag)

        return matched_tags

    def log_events(self, camera_name: str, observation: dict) -> list[str]:
        """Match and log events. Only observations that match at least one
        event are written — unmatched observations are skipped."""
        tags = self.match(camera_name, observation)

        # Nothing matched — don't log this observation at all.
        if not tags:
            return tags

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Which matched tags are notify events, and whether any fired.
        notify_tags = [t for t in tags if t in self._notify_tags]
        notify      = bool(notify_tags)

        # Build a short 5-word summary from observation
        parts = [
            _as_text(observation.get("actions")),
            _as_text(observation.get("people")),
            _as_text(observation.get("objects")),
        ]
        combined  = ", ".join(p for p in parts if p)
        words     = combined.replace(",", "").split()
        summary   = " ".join(words[:5]) if words else "nothing observed"

        entry = {
            "ts":          ts,
            "cam":         camera_name,
            "summary":     summary,
            "tags":        tags,
            "notify":      notify,
            "notify_tags": notify_tags,
        }

        marker = " [NOTIFY]" if notify else ""
        log.info(f"[{camera_name}] {summary} | {', '.join(tags)}{marker}")
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

        return tags

    def log_timeout(self, camera_name: str):
        """Log an LLM timeout event."""
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "ts":          ts,
            "cam":         camera_name,
            "summary":     "LLM timeout no response",
            "tags":        ["LLM_TIMEOUT"],
            "notify":      False,
            "notify_tags": [],
        }
        log.warning(f"[{camera_name}] LLM_TIMEOUT")
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

    def close(self):
        self._file.close()