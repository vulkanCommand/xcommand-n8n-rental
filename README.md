# xcommand – n8n Rental Platform

This repo contains everything needed to run the xcommand n8n rental platform:
- API + provisioning logic
- Landing/payment web app
- Background workers
- Janitor/cleanup service
- Infrastructure definitions for n8n, Traefik, and Caddy

The goal is that anyone can:
1. Run the full stack locally.
2. Deploy to a Docker host (Hostinger, VPS, etc).
3. Migrate to a new cloud later (AWS, etc) using the same repo.

---

## Folder structure

**Root**

- `docker-compose.yml`  
  Orchestrates the core services (API, web, worker, janitor, DB, etc).

- `docker-compose.override.yml`  
  Optional overrides (local dev, extra mounts, etc).

- `migrations/`  
  Database schema and migration SQL (e.g. `001_init.sql`).

- `scripts/`  
  Helper scripts (e.g. `ws.sh` for workspace-related tasks).

- `landing/`  
  Static HTML landing page (`index.html`), used by the web frontend.

- `traefik/`  
  Traefik config used by the main stack (separate from the n8n infra).

---

## Services

### `api/`

FastAPI backend and provisioning logic.

Key files:
- `main.py` – FastAPI entrypoint.
- `db.py` – Database connection/config.
- `provisioner.py` – Workspace provisioning logic.
- `n8n_templates/` – Any templates used when spinning up n8n workspaces.
- `requirements.txt` – Python dependencies.
- `Dockerfile` – API service container definition.

### `web/`

Small web service (FastAPI or simple server) that serves the UI pages:
- `index.html`, `pay.html`, `ready.html`, `test.html`.
- `app.py` – Handles basic routes for the landing / payment pages.
- `Dockerfile` – Web service container.

### `worker/`

Background worker process (queue/async jobs, emails, etc):
- `worker.py`
- `requirements.txt`
- `Dockerfile`

### `janitor/`

Cleanup service that checks for expired workspaces and tears them down:
- `janitor.py`
- `app.py`
- `requirements.txt`
- `Dockerfile`

---

## Infrastructure (`infra/`)

This folder describes how supporting services are run.

### `infra/n8n/`

Infrastructure specifically for n8n + Traefik:

- `docker-compose.yml` – n8n + Traefik stack.
- `traefik/dynamic.yml` – Dynamic routing config for Traefik.
- `traefik/dynamic/www-redirect.yml` – Redirect rules for `www` → root, etc.

### `infra/caddy/`

- `Caddyfile` – Caddy reverse proxy configuration used on the server.

### `infra/legacy/`

- `root-docker-compose.yml` – Older/legacy compose previously used from `/root` on the server. Kept for reference and possible rollback; not used in the current setup.

---

## How to use this repo (high level)

1. **Local dev**
   - Use `docker-compose.yml` to spin up API, DB, web, worker, janitor.
   - Use `.env` files (not committed) for secrets and environment-specific config.

2. **Production / VPS**
   - Clone this repo onto the server.
   - Use the main `docker-compose.yml` to start the stack.
   - Use `infra/n8n/docker-compose.yml` for the dedicated n8n cluster.
   - Use `infra/caddy/Caddyfile` (or Traefik configs) for TLS + routing.

3. **Future cloud migration**
   - All important logic, configs, and infra definitions live in this repo.
   - You can map these Docker configs into AWS ECS, App Runner, or another Docker host later.

---

## Env files and secrets

- Secrets are **not** committed to the repo.
- Keep env files (e.g. `.env`) local or in a secrets manager.
- `.env.example` (if present) should list all required variables.

---

## Next steps

- [ ] Refine local dev docker-compose for easy `docker compose up`.
- [ ] Add documentation for how to bring up the stack locally.
- [ ] Optionally add CI/CD for deploying from GitHub to production.
