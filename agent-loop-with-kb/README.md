# knitwit-agent

A standalone Manager + Developer coding agent. Point it at any project and give it a task.

## Setup

```bash
git clone https://github.com/you/knitwit-agent
cd knitwit-agent
pip install -r requirements.txt
```

## Configure

Edit `agent.config.json`:

```json
{
  "project_path": "../knitwit",
  "manager":   { "provider": "anthropic", "model": "claude-opus-4-5",  "api_key_env": "ANTHROPIC_API_KEY" },
  "developer": { "provider": "anthropic", "model": "claude-sonnet-4-6", "api_key_env": "ANTHROPIC_API_KEY" }
}
```

Then set your API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
# project_path from config
python main.py "Add a drop-shoulder pattern"

# override project at runtime
python main.py --project /path/to/any/project "Refactor the utils folder"

# different config file
python main.py --config ~/my-config.json "Add dark mode"

# interactive
python main.py
```

## Supported providers

| Provider | `provider` value | `api_key_env` | `base_url` |
|---|---|---|---|
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | — |
| OpenAI | `openai` | `OPENAI_API_KEY` | — |
| Groq | `groq` | `GROQ_API_KEY` | `https://api.groq.com/openai/v1` |
| Together AI | `together` | `TOGETHER_API_KEY` | `https://api.together.xyz/v1` |
| Mistral | `mistral` | `MISTRAL_API_KEY` | `https://api.mistral.ai/v1` |
| Ollama (local) | `ollama` | — | `http://localhost:11434/v1` |

Mix and match — manager and developer can be different providers.

## How to give the agent access to a project

Two things are all it needs:

1. **`project_path`** in config (or `--project` flag) — tells the agent where the files are
2. **`CLAUDE.md`** in the project root — tells the agent what the project is and how to work on it

The agent can read, write, and run commands inside that folder. Nothing else.

## CLAUDE.md

Add a `CLAUDE.md` to any project you want the agent to work on:

```markdown
# My Project

## What this is
A React + Vite app that does X.

## How to verify changes
npm run build

## Conventions
- All components in src/components/
- No TypeScript
- ...
```

The agent reads this before every task. It's how you encode your project's rules.

## Adding a new provider

1. Create `providers/your_provider.py` implementing `BaseProvider`
2. Add it to the factory in `providers/__init__.py`

That's it.
