# Knitwit Agent

An autonomous coding agent that picks up tasks from your Jira board, writes the code, reviews it, tests it, and pushes a branch — all by running a single command.

```
python main.py
```

---

## How it works

```
python main.py
    ↓
Pulls next "To Do" ticket from Jira
    ↓
Creates a branch  feat/KAN-2-your-ticket
    ↓
Manager    plans the work
Developer  writes the code
Reviewer   checks quality
Tester     runs the build
    ↓
Pushes branch → Jira ticket → Resolved
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-..."
$env:JIRA_EMAIL="your@email.com"
$env:JIRA_API_TOKEN="your-token"

# Mac / Linux
export OPENAI_API_KEY="sk-..."
export JIRA_EMAIL="your@email.com"
export JIRA_API_TOKEN="your-token"
```

Get your Jira API token at:
`https://id.atlassian.com/manage-profile/security/api-tokens`

### 3. Configure

Edit `agent.config.json`:

```json
{
  "project_path": "/path/to/your/project",

  "jira": {
    "base_url":           "https://yourname.atlassian.net",
    "email_env":          "JIRA_EMAIL",
    "token_env":          "JIRA_API_TOKEN",
    "project_key":        "KAN",
    "pull_status":        "To Do",
    "in_progress_status": "In Progress",
    "done_status":        "Resolved"
  },

  "manager":   { "provider": "openai", "model": "gpt-4o",      "api_key_env": "OPENAI_API_KEY" },
  "developer": { "provider": "openai", "model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY" },
  "reviewer":  { "provider": "openai", "model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY" },
  "tester":    { "provider": "openai", "model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY" }
}
```

### 4. Add a CLAUDE.md to your project

The agent reads this before every task. Tell it what your project is and how to work on it:

```markdown
# My Project

## What this is
A React + Vite app that does X.

## How to verify changes
npm run build

## Conventions
- All components in src/components/
- No TypeScript
```

---

## Run

```bash
# Let it pick the next Jira ticket automatically
python main.py

# Or give it a task directly (skips Jira)
python main.py "Add a drop-shoulder pattern"

# Point at a specific local project
python main.py --project /path/to/project "Fix the gauge calculation"

# Clone and work on a remote repo
python main.py --repo https://github.com/you/repo "Add dark mode"
python main.py --repo https://github.com/you/repo --branch dev "Add dark mode"
```

---

## Ticket naming convention

The agent uses the ticket **summary as the filename** and the **description as the instruction**:

| Ticket | Summary | Description |
|---|---|---|
| KAN-2 | `jira_utils.py` | Add Jira REST API integration |
| KAN-3 | `src/patterns/dropShoulder.js` | Add drop-shoulder pattern following raglanMockNeck.js |
| KAN-4 | `Add dark mode` | *(description optional — agent figures it out)* |

---

## Supported providers

| Provider | `provider` value | `api_key_env` | `base_url` |
|---|---|---|---|
| OpenAI | `openai` | `OPENAI_API_KEY` | — |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | — |
| Groq | `groq` | `GROQ_API_KEY` | `https://api.groq.com/openai/v1` |
| Mistral | `mistral` | `MISTRAL_API_KEY` | `https://api.mistral.ai/v1` |
| Ollama (local) | `ollama` | — | `http://localhost:11434/v1` |

Each agent node (manager, developer, reviewer, tester) can use a different provider and model.

---

## Project structure

```
main.py          ← entry point — this is all you need to run
nodes.py         ← manager, developer, reviewer, tester agents
graph.py         ← LangGraph state machine wiring
state.py         ← shared state flowing through every node
agents.py        ← system prompts
tools.py         ← file and shell tools the agents can use
config.py        ← model factory
jira_utils.py    ← Jira board integration
git_utils.py     ← branch creation and push
agent.config.json ← your configuration
```