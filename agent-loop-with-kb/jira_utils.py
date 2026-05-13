"""
Jira integration for the agent.

Fetches the next ticket from the board, transitions status as the agent
progresses, and marks it done when finished.

Uses the Jira REST API v3 directly — no extra libraries needed beyond
what's already installed (requests).

Setup:
  1. Get your API token at: https://id.atlassian.com/manage-profile/security/api-tokens
  2. Set env vars:
       JIRA_EMAIL=your@email.com
       JIRA_API_TOKEN=your-token
  3. Add a "jira" section to agent.config.json (see below)

agent.config.json jira section:
  {
    "jira": {
      "base_url":           "https://shraddhajasinska.atlassian.net",
      "email_env":          "JIRA_EMAIL",
      "token_env":          "JIRA_API_TOKEN",
      "project_key":        "KAN",
      "pull_status":        "To Do",
      "in_progress_status": "In Progress",
      "done_status":        "Resolved"
    }
  }
"""

import os
import requests
from requests.auth import HTTPBasicAuth
from rich.console import Console

console = Console()


class JiraClient:
    def __init__(self, cfg: dict):
        self.base_url    = cfg["base_url"].rstrip("/")
        self.project_key = cfg["project_key"]
        self.pull_status        = cfg.get("pull_status",        "To Do")
        self.in_progress_status = cfg.get("in_progress_status", "In Progress")
        self.done_status        = cfg.get("done_status",        "Resolved")

        email = os.environ.get(cfg.get("email_env", "JIRA_EMAIL"), "")
        token = os.environ.get(cfg.get("token_env", "JIRA_API_TOKEN"), "")

        if not email or not token:
            raise EnvironmentError(
                "Jira credentials missing. Set JIRA_EMAIL and JIRA_API_TOKEN env vars.\n"
                "Get your token at: https://id.atlassian.com/manage-profile/security/api-tokens"
            )

        self.auth    = HTTPBasicAuth(email, token)
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # ── Fetch ─────────────────────────────────────────────────────────────────

    def fetch_next_ticket(self) -> dict | None:
        """
        Returns the oldest ticket in pull_status as a dict:
          { id, key, summary, description }
        Returns None if no tickets are found.
        """
        jql = (
            f"project = {self.project_key} "
            f'AND status = "{self.pull_status}" '
            f"ORDER BY created ASC"
        )
        # Atlassian deprecated GET /search — use POST /search/jql instead
        url = f"{self.base_url}/rest/api/3/search/jql"
        resp = requests.post(
            url,
            auth=self.auth,
            headers=self.headers,
            json={
                "jql": jql,
                "maxResults": 1,
                "fields": ["summary", "description", "status"],
            },
        )
        resp.raise_for_status()
        issues = resp.json().get("issues", [])

        if not issues:
            return None

        issue  = issues[0]
        fields = issue["fields"]

        # Description is Atlassian Document Format (ADF) — extract plain text
        description = _adf_to_text(fields.get("description")) or "(no description)"

        return {
            "id":          issue["id"],
            "key":         issue["key"],
            "summary":     fields["summary"],
            "description": description,
        }

    # ── Transitions ───────────────────────────────────────────────────────────

    def get_transitions(self, issue_key: str) -> list[dict]:
        """Return all available transitions for an issue."""
        url  = f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
        resp = requests.get(url, auth=self.auth, headers=self.headers)
        resp.raise_for_status()
        return resp.json().get("transitions", [])

    def transition(self, issue_key: str, target_status: str) -> bool:
        """
        Transition an issue to target_status by name.
        Returns True on success, False if the transition wasn't found.
        """
        transitions = self.get_transitions(issue_key)
        match = next(
            (t for t in transitions if t["to"]["name"].lower() == target_status.lower()),
            None,
        )
        if not match:
            console.print(
                f"[yellow]Jira: transition to '{target_status}' not available for {issue_key}[/yellow]\n"
                f"Available: {[t['to']['name'] for t in transitions]}"
            )
            return False

        url  = f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
        resp = requests.post(
            url,
            auth=self.auth,
            headers=self.headers,
            json={"transition": {"id": match["id"]}},
        )
        resp.raise_for_status()
        return True

    def start_ticket(self, issue_key: str):
        """Transition ticket to In Progress."""
        ok = self.transition(issue_key, self.in_progress_status)
        if ok:
            console.print(f"[dim]Jira: {issue_key} → {self.in_progress_status}[/dim]")

    def complete_ticket(self, issue_key: str):
        """Transition ticket to done status."""
        ok = self.transition(issue_key, self.done_status)
        if ok:
            console.print(f"[dim]Jira: {issue_key} → {self.done_status}[/dim]")

    def add_comment(self, issue_key: str, text: str):
        """Post a comment on a ticket (e.g. agent summary)."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        requests.post(
            url,
            auth=self.auth,
            headers=self.headers,
            json={"body": {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": text}]}
            ]}},
        )


# ── ADF → plain text ──────────────────────────────────────────────────────────

def _adf_to_text(adf: dict | None) -> str:
    """
    Recursively extract plain text from Atlassian Document Format.
    ADF is a nested JSON structure — we just want the readable text.
    """
    if not adf:
        return ""
    if isinstance(adf, str):
        return adf
    if adf.get("type") == "text":
        return adf.get("text", "")
    parts = []
    for node in adf.get("content", []):
        part = _adf_to_text(node)
        if part:
            parts.append(part)
    return " ".join(parts)


# ── Factory ───────────────────────────────────────────────────────────────────

def make_jira_client(cfg: dict) -> JiraClient | None:
    """
    Build a JiraClient from the full agent config.
    Returns None if no 'jira' section is present — Jira is optional.
    """
    jira_cfg = cfg.get("jira")
    if not jira_cfg:
        return None
    return JiraClient(jira_cfg)


# ── Task formatter ────────────────────────────────────────────────────────────

def format_task(summary: str, description: str, key: str = "") -> str:
    """
    Build the task string the agent receives.

    Ticket naming convention:
      Summary     = the target filename  e.g. "jira_utils.py"
      Description = what to do with it  e.g. "Add Jira REST API integration..."

    The agent receives a clear, unambiguous instruction combining both.
    """
    summary = summary.strip()
    description = description.strip()

    # Detect if summary looks like a filename (has an extension or path separator)
    is_filename = (
        "." in summary.split("/")[-1]          # has extension: jira_utils.py
        or "/" in summary                       # has path: src/utils/gauge.js
        or "\\" in summary                      # Windows path
    )

    if is_filename and description and description != "(no description)":
        return (
            f"Work on the file: {summary}\n\n"
            f"Instructions:\n{description}"
        )

    if is_filename and (not description or description == "(no description)"):
        # No description — agent figures it out from CLAUDE.md + the filename
        return f"Work on the file: {summary}"

    # Not a filename — treat summary as a plain task title
    if description and description != "(no description)":
        return f"{summary}\n\n{description}"

    return summary