# LaTeX Dev Environment — MiKTeX + code-server

A self-contained LaTeX environment that runs in Docker and is accessible via your browser.

## Stack
| Component | Details |
|---|---|
| LaTeX distro | MiKTeX (auto-installs missing packages) |
| Editor | code-server (VS Code in the browser) |
| Extension | LaTeX Workshop (auto-build on save, PDF preview) |

---

## Quick Start

```bash
# 1. Build & start
docker compose up --build

# 2. Open your browser
open http://localhost:8080

# 3. Open workspace/main.tex and start writing!
```

The first build takes a few minutes (MiKTeX is ~500 MB).  
Subsequent starts are fast thanks to the `miktex-cache` volume.

---

## Usage

- **Auto-build**: saves trigger a compile automatically.
- **Manual build**: `Ctrl+Alt+B` (or click the green ▶ in the LaTeX Workshop sidebar).
- **PDF preview**: opens in a side tab — use `Ctrl+Alt+V`.
- **Change compiler**: open the LaTeX Workshop sidebar → pick a recipe (pdfLaTeX, XeLaTeX, LuaLaTeX, etc.).
- **Your files**: put everything inside `./workspace/` — it's bind-mounted into the container.

---

## Stopping & Restarting

```bash
docker compose down        # stop (workspace files are safe)
docker compose up          # restart (no rebuild needed)
docker compose up --build  # rebuild image (after Dockerfile changes)
```

---

## Adding Packages Manually

MiKTeX auto-installs packages on first compile. To install manually:

```bash
docker exec -it latex-dev mpm --install <package-name>
```

---

## Security Note

`config.yaml` sets `auth: none` — fine for local use. If you expose port 8080
publicly, set a password:

```yaml
auth: password
password: your-strong-password
```