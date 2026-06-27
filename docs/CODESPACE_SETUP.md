# Codespace Local Dev Setup

All commands assume you're in `/workspaces/medical`.

---

## Quick start (one command)

```bash
./scripts/dev-start.sh
```

This script is **idempotent** — safe to run at the start of every session, after
a rebuild, or whenever things look broken. It:

1. Starts PostgreSQL (if not running)
2. Creates the `medvault` user and database (if missing), resets the password
3. Creates `backend/.env` from template (if missing)
4. Installs backend Python dependencies
5. Runs `alembic upgrade head` (creates/updates all tables)
6. Installs frontend npm dependencies (if needed)
7. Creates `frontend/.env` from template (if missing)
8. Prints the env values you need to set for the Codespace URLs

After the script finishes, follow the printed instructions to set `CORS_ORIGINS`
and `VITE_API_BASE_URL`, then start the servers.

---

## Manual steps (if you prefer)

### 1. Start PostgreSQL

```bash
sudo su - postgres -c "pg_ctlcluster 16 main start"
```

### 2. Create user and database

```bash
sudo su - postgres -c "psql -c \"CREATE USER medvault WITH PASSWORD 'medvault';\""
sudo su - postgres -c "psql -c \"CREATE DATABASE medvault OWNER medvault;\""
```

If the user/db already exist, these will error harmlessly. To reset the password:

```bash
sudo su - postgres -c "psql -c \"ALTER USER medvault WITH PASSWORD 'medvault';\""
```

### 3. Backend setup

```bash
cd backend
cp .env.example .env     # edit CORS_ORIGINS for your Codespace
pip install -e ".[dev]"
alembic upgrade head
```

### 4. Frontend setup

```bash
cd frontend
cp .env.example .env     # edit VITE_API_BASE_URL for your Codespace
npm install
```

### 5. Configure Codespace URLs

Find your codespace name:
```bash
echo $CODESPACE_NAME
```

Set in `backend/.env`:
```
CORS_ORIGINS=https://<codespace-name>-5173.app.github.dev
```

Set in `frontend/.env`:
```
VITE_API_BASE_URL=https://<codespace-name>-8000.app.github.dev
```

**Make port 8000 PUBLIC** in the Codespace Ports tab.

### 6. Start servers

```bash
# Terminal 1 — Backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open `https://<codespace-name>-5173.app.github.dev` in your browser.

---

## After a Codespace rebuild

Run `./scripts/dev-start.sh` — it handles everything. Your `.env` files survive
if the workspace volume is preserved. If not, the script recreates them from
the committed `.env.example` templates.

**Data**: if Postgres data was wiped by the rebuild, `alembic upgrade head`
recreates all tables (empty). If the data survived, Alembic says "already at head."

---

## Running tests

```bash
# Backend
cd backend
DATABASE_URL="postgresql+asyncpg://medvault:medvault@localhost:5432/medvault" python -m pytest tests/ -v

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
| `UPLOAD_DIR` | `./uploads` | Local file storage directory |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` (10 MB) | Max upload file size |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend URL (no `/api/v1`, no trailing slash) |
