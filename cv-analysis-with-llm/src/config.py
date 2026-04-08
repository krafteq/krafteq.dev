import os
import yaml
import logging
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)


class Config:
    def __init__(self):
        self.ollama_host    = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.llm_model      = os.getenv("LLM_MODEL", "llava")
        self.fps            = int(os.getenv("FPS", "5"))
        self.buffer_seconds = int(os.getenv("BUFFER_SECONDS", "5"))
        self.camera_mode    = os.getenv("CAMERA_MODE", "single")  # single | multi (future)
        self._cameras       = self._load_cameras()

    def _load_cameras(self) -> list[dict]:
        path = os.getenv("CAMERAS_CONFIG", "cameras.yaml")
        if not os.path.exists(path):
            log.warning(f"cameras.yaml not found at '{path}'")
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("cameras", [])

    @property
    def active_camera(self) -> dict | None:
        """Returns the first active camera (single mode)."""
        for cam in self._cameras:
            if cam.get("active", False):
                return cam
        return None

    @property
    def all_active_cameras(self) -> list[dict]:
        """Returns all active cameras (for future multi mode)."""
        return [c for c in self._cameras if c.get("active", False)]

    @property
    def events(self) -> list[dict]:
        """Returns event definitions from cameras.yaml."""
        path = os.getenv("CAMERAS_CONFIG", "cameras.yaml")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("events", [])


cfg = Config()