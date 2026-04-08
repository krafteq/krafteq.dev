import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)


class Notifier:
    def __init__(self):
        self.enabled   = os.getenv("NOTIFICATIONS_ENABLED", "false").lower() == "true"
        self.sender    = os.getenv("GMAIL_SENDER", "")
        self.password  = os.getenv("GMAIL_APP_PASSWORD", "")
        self.recipient = os.getenv("GMAIL_RECIPIENT", "")
        self.keywords  = [
            k.strip().lower()
            for k in os.getenv("NOTIFY_ON_KEYWORDS", "").split(",")
            if k.strip()
        ]

        if self.enabled:
            if not all([self.sender, self.password, self.recipient]):
                log.warning("Notifications enabled but Gmail credentials incomplete — disabling")
                self.enabled = False
            else:
                log.info(f"Notifications enabled → {self.recipient} | keywords: {self.keywords or 'all'}")
        else:
            log.info("Notifications disabled (NOTIFICATIONS_ENABLED=false)")

    def _should_notify(self, observation: dict) -> bool:
        """If no keywords set, notify on every observation. Otherwise match keywords."""
        if not self.keywords:
            return True
        combined = " ".join([
            observation.get("objects", "") or "",
            observation.get("people",  "") or "",
            observation.get("actions", "") or "",
        ]).lower()
        return any(kw in combined for kw in self.keywords)

    def _build_email(self, camera_name: str, observation: dict) -> MIMEMultipart:
        ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Diary Log] Activity detected — {camera_name}"
        msg["From"]    = self.sender
        msg["To"]      = self.recipient

        body = f"""
Activity detected on camera: {camera_name}
Time: {ts}

Objects : {observation.get('objects', 'N/A')}
People  : {observation.get('people',  'N/A')}
Actions : {observation.get('actions', 'N/A')}
        """.strip()

        msg.attach(MIMEText(body, "plain"))
        return msg

    def notify(self, camera_name: str, observation: dict):
        """Send email notification if enabled and observation matches keywords."""
        if not self.enabled:
            return
        if not self._should_notify(observation):
            return

        try:
            msg = self._build_email(camera_name, observation)
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender, self.password)
                server.sendmail(self.sender, self.recipient, msg.as_string())
            log.info(f"[{camera_name}] Notification sent → {self.recipient}")
        except smtplib.SMTPAuthenticationError:
            log.error("Gmail auth failed — check GMAIL_SENDER and GMAIL_APP_PASSWORD")
        except Exception as e:
            log.exception(f"Failed to send notification: {e}")