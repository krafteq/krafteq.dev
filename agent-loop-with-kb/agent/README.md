# Knitwit Agent

A Manager + Developer agent pair that can extend the Knitwit project autonomously.

## Setup

```bash
cd agent
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
# Pass a task directly
python main.py "Add a drop-shoulder pattern"

# Interactive mode
python main.py
```

## Example tasks

```bash
python main.py "Add a drop-shoulder sweater pattern"
python main.py "Add ease controls to PatternForm — positive ease in cm"
python main.py "Expose upper arm circumference as an optional custom input"
python main.py "Add a schematic measurements summary card below the pattern output"
```

## How it works

```
You (task)
  → Manager reads CLAUDE.md, plans steps
    → Developer reads files, writes code, runs npm run build
      → Manager reviews build output
        → DONE or REVISION loop
```

### Manager (claude-opus-4-5)
- Reads CLAUDE.md on every run
- Breaks tasks into steps
- Reviews developer output
- Approves or requests changes

### Developer (claude-sonnet-4-6)
- Has 4 tools: read_file, write_file, list_directory, run_command
- Always reads existing code before writing
- Always runs `npm run build` after changes
- Reports full results back to Manager

## Files

```
agent/
  main.py       ← CLI entry point
  loop.py       ← orchestration logic
  agents.py     ← system prompts + model config
  tools.py      ← tool implementations
  requirements.txt
```
