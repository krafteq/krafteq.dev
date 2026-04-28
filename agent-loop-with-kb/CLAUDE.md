# Knitwit — Agent Briefing

## What this project is
A knitting sweater pattern generator. The user inputs yarn gauge and target size,
selects a pattern style, and receives complete row-by-row knitting instructions.
Pure math — no AI involved in pattern generation. React + Vite + Tailwind. No backend.

## Project structure
```
src/
  App.jsx                    ← root component, wires form + output
  components/
    PatternForm.jsx           ← gauge inputs, size picker (preset/custom)
    PatternOutput.jsx         ← renders instruction text + copy button
  patterns/
    raglanMockNeck.js         ← THE reference pattern — read this first
  utils/
    gauge.js                  ← cmToSt(), cmToRow(), roundEven()
    presets.js                ← XS–XXL size registry
CLAUDE.md                     ← this file
agent/                        ← agent code lives here, not in src/
```

## Adding a new pattern (the most common task)
1. Read `src/patterns/raglanMockNeck.js` first — it is the reference implementation
2. Create `src/patterns/yourPatternName.js`
3. Export exactly these three functions:
   - `compute(gauge, measurements)` → plain object of all calculated numbers
   - `validateInputs(gauge, measurements)` → array of error strings (empty = valid)
   - `buildInstructions(stats)` → string of knitting instructions
4. Register the new pattern in `src/components/PatternForm.jsx`

## Math rules — never break these
- All stitch counts MUST be even numbers — always use `roundEven()` from utils/gauge.js
- Row counts use plain `Math.round()`
- Never hardcode measurements — always derive from gauge + user inputs
- Underarm stitches minimum is 4 (use `Math.max(4, ...)`)
- Increase/decrease intervals minimum is 2 rows (use `Math.max(2, ...)`)

## Code style
- ES modules throughout (`import`/`export`, not `require`)
- No TypeScript — plain JS
- Tailwind for all styling — no custom CSS files
- Components are small and focused — if a component grows past ~120 lines, split it

## Verification — a task is NOT done until this passes
```bash
npm run build
```
Always run this after any file changes. A build error means the task failed.

## What not to touch
- `agent/` directory — that's the agent's own code, don't modify it from within tasks
- `package.json` dependencies — don't add packages without asking the user
- Existing pattern math in `raglanMockNeck.js` — treat it as stable reference
