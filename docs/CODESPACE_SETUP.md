# Codespace Dev Setup

All commands assume you're in `/workspaces/medical`.

---

## Quick start (one command)

```bash
./scripts/dev-start.sh
```

Run this at the start of every session, after a rebuild, or whenever things
look broken. It is **fully idempotent** — repeat runs are safe.

### What it does

1. Starts PostgreSQL (skips if already running)
2. Creates the `medvault` role and database if missing
3. Creates `backend/.env` from the template if missing; syncs the DB password
4. Installs backend Python dependencies (`pip install -e ".[dev]"`)
5. Runs `alembic upgrade head`; auto-recovers if the schema is missing
6. Installs frontend npm dependencies if `node_modules` is absent
7. **Writes** `VITE_API_BASE_URL` and `CORS_ORIGINS` into the env files using
   the `$CODESPACE_NAME` forwarding domain — overwrites any localhost or
   stale Codespace value; never touches custom (non-localhost) values
8. Makes ports **8000** and **5173** public via `gh codespace ports visibility`
   (falls back to printed instructions if gh CLI is unavailable)
9. Kills any stale processes on :8000 and :5173
10. Starts uvicorn on :8000 and Vite on :5173 in the background
11. Waits up to 30 s for both servers to respond
12. Prints the **exact forwarded URL** to open and whether the **DB is empty**
    (so you know to register fresh or log in)

When the script finishes you get output like:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open:  https://<codespace>-5173.app.github.dev
  API:   https://<codespace>-8000.app.github.dev/api/v1/health

  DB is empty — register a new account to get started.

  Logs:  tail -f /tmp/medvault-backend.log
         tail -f /tmp/medvault-frontend.log
  Stop:  kill <be-pid> <fe-pid>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## After a Codespace rebuild

Run `./scripts/dev-start.sh`. If the workspace volume survived, your `.env`
files and Postgres data are intact; Alembic says "already at head." If the
volume was wiped, the script recreates `.env` from the committed templates and
rebuilds the schema from scratch.

---

## Stopping the servers

```bash
kill <be-pid> <fe-pid>    # PIDs shown in the summary
```

Or just close the terminal; the background processes die with the session.

---

## Manual steps (if you prefer not to use the script)

### 1. Start PostgreSQL

```bash
sudo su - postgres -c "pg_ctlcluster 16 main start"
```

### 2. Create user and database

```bash
sudo su - postgres -c "psql -c \"CREATE USER medvault WITH PASSWORD 'medvault';\""
sudo su - postgres -c "psql -c \"CREATE DATABASE medvault OWNER medvault;\""
```

### 3. Backend setup

```bash
cd backend
cp .env.example .env
pip install -e ".[dev]"
alembic upgrade head
```

### 4. Frontend setup

```bash
cd frontend
cp .env.example .env
npm install
```

### 5. Configure Codespace URLs

```bash
echo $CODESPACE_NAME   # find your codespace name
```

Edit `backend/.env`:
```
CORS_ORIGINS=https://<codespace-name>-5173.app.github.dev
```

Edit `frontend/.env`:
```
VITE_API_BASE_URL=https://<codespace-name>-8000.app.github.dev
```

Make ports public:
```bash
gh codespace ports visibility 8000:public 5173:public -c $CODESPACE_NAME
```
Or use the **Ports** tab in the Codespaces UI.

### 6. Start servers

```bash
# Terminal 1 — Backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open `https://<codespace-name>-5173.app.github.dev`.

---

## Running tests

```bash
# Backend
cd backend
DATABASE_URL="postgresql+asyncpg://medvault:medvault@localhost:5432/medvault" \
  python -m pytest tests/ -v

# Frontend
cd frontend
npm test
```

---

## Environment variable reference

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://medvault:medvault@localhost:5432/medvault` | Async Postgres connection |
| `JWT_SECRET_KEY` | `change-me-to-a-random-secret` | JWT signing key |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `UPLOAD_DIR` | `./uploads` | Local file storage |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` (10 MB) | Max upload size |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend URL (no `/api/v1`, no trailing slash) |
