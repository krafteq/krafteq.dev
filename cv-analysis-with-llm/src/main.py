import os
import logging
from config import cfg
from detector import CameraDetector

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/detector.log")
    ]
)
log = logging.getLogger(__name__)


if __name__ == "__main__":
    camera = cfg.active_camera
    if not camera:
        log.error("No active camera found in vision_config.yaml")
    else:
        log.info(f"Starting with camera: {camera['name']} ({camera['type']})")
        CameraDetector(camera).run()