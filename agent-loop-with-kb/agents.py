"""
System prompts for each agent node.
CLAUDE.md is loaded fresh on every manager call.
"""

from pathlib import Path

_project_root: Path = Path(".")


def set_project_root(p: Path):
    global _project_root
    _project_root = p.resolve()


def _load_claude_md() -> str:
    path = _project_root / "CLAUDE.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "(No CLAUDE.md found — proceed using general best practices)"


# ── Manager ───────────────────────────────────────────────────────────────────

def manager_prompt(task: str, tester_feedback: str = "") -> str:
    context = (
        f"Tester feedback:\n{tester_feedback}"
        if tester_feedback
        else f"Task: {task}"
    )
    return f"""You are the Manager of a software project.

Project briefing (CLAUDE.md):
──────────────────────────────
{_load_claude_md()}
──────────────────────────────

{context}

Your job:
- If this is the first call: create a clear step-by-step plan for the Developer.
- If reviewing tester feedback: decide if the task is complete or needs more work.

End your response with exactly one of:
  DECISION: work   <- developer should implement / continue
  DECISION: done   <- task is complete and verified"""


# ── Developer ─────────────────────────────────────────────────────────────────

def developer_prompt(task: str, plan: str, feedback: str = "") -> str:
    extra = f"\nFeedback to address:\n{feedback}" if feedback else ""
    return f"""You are a Developer implementing a task in this software project.

Manager's plan:
{plan}

Task:
{task}
{extra}

Instructions:
- Read relevant existing files before making changes.
- Follow the project conventions from CLAUDE.md.
- After making changes, run the project build command to verify compilation.
- Report exactly what you changed and what the build output was."""


# ── Reviewer ──────────────────────────────────────────────────────────────────

def reviewer_prompt(task: str, dev_output: str) -> str:
    return f"""You are a Code Reviewer checking a developer's work.

Task that was implemented:
{task}

Developer's summary:
{dev_output}

Review the actual files in the project. Check:
- Does it follow project conventions?
- Is the logic correct?
- Are there obvious bugs or missing edge cases?
- Does it integrate cleanly with existing code?

End your response with exactly one of:
  DECISION: approved      <- ready for testing
  DECISION: needs_changes <- describe issues clearly above"""


# ── Tester ────────────────────────────────────────────────────────────────────

def tester_prompt(task: str, dev_output: str) -> str:
    return f"""You are a Tester verifying that a developer's implementation works.

Task that was implemented:
{task}

Developer's summary:
{dev_output}

Steps:
1. Run the project build command (check CLAUDE.md or package.json).
2. Check for errors or warnings.
3. Report the full build output.

End your response with exactly one of:
  DECISION: passed <- build succeeded with no errors
  DECISION: failed <- describe exactly what failed"""