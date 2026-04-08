import logging
import json
import os
from datetime import datetime

log = logging.getLogger(__name__)

EVENTS_LOG_FILE = os.getenv("EVENTS_LOG_FILE", "logs/events.log")


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

            search_text = " ".join([
                observation.get(f, "") or "" for f in fields
            ]).lower()

            if any(kw in search_text for kw in keywords):
                matched_tags.append(tag)

        return matched_tags

    def log_events(self, camera_name: str, observation: dict) -> list[str]:
        """Match and log events. Always writes a summary, tags if matched."""
        tags = self.match(camera_name, observation)

        ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build a short 5-word summary from observation
        parts = [
            observation.get("actions") or "",
            observation.get("people")  or "",
            observation.get("objects") or "",
        ]
        combined  = ", ".join(p for p in parts if p)
        words     = combined.replace(",", "").split()
        summary   = " ".join(words[:5]) if words else "nothing observed"

        entry = {
            "ts":      ts,
            "cam":     camera_name,
            "summary": summary,
            "tags":    tags if tags else [],
        }

        log.info(f"[{camera_name}] {summary}" + (f" | {', '.join(tags)}" if tags else ""))
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

        return tags

    def log_timeout(self, camera_name: str):
        """Log an LLM timeout event."""
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "ts":      ts,
            "cam":     camera_name,
            "summary": "LLM timeout no response",
            "tags":    ["LLM_TIMEOUT"],
        }
        log.warning(f"[{camera_name}] LLM_TIMEOUT")
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

    def close(self):
        self._file.close()