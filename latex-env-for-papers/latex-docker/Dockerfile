FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# ── System dependencies ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    dirmngr \
    gnupg \
    lsb-release \
    perl \
    python3 \
    wget \
    git \
    make \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# ── MiKTeX ─────────────────────────────────────────────────────────────────────
RUN curl -fsSL https://miktex.org/download/key | gpg --dearmor -o /usr/share/keyrings/miktex-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/miktex-keyring.gpg] https://miktex.org/download/ubuntu jammy universe" \
       > /etc/apt/sources.list.d/miktex.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends miktex \
    && rm -rf /var/lib/apt/lists/*

# Finish MiKTeX setup & enable auto-install of missing packages
RUN miktexsetup --shared=yes finish \
    && initexmf --admin --set-config-value "[MPM]AutoInstall=1" \
    && mpm --admin --update-db

# ── code-server (browser VS Code) ─────────────────────────────────────────────
RUN curl -fsSL https://code-server.dev/install.sh | sh

# ── LaTeX Workshop extension ───────────────────────────────────────────────────
RUN code-server --install-extension James-Yu.latex-workshop --force

# ── Workspace ─────────────────────────────────────────────────────────────────
RUN mkdir -p /workspace
WORKDIR /workspace

# ── code-server config ─────────────────────────────────────────────────────────
RUN mkdir -p /root/.config/code-server
COPY config.yaml /root/.config/code-server/config.yaml

# ── LaTeX Workshop settings ────────────────────────────────────────────────────
RUN mkdir -p /root/.local/share/code-server/User
COPY settings.json /root/.local/share/code-server/User/settings.json

EXPOSE 8080

CMD ["code-server", "--bind-addr", "0.0.0.0:8080", "/workspace"]