# Codespace Local Dev Setup

Step-by-step instructions to run MedVault (backend + frontend) in a GitHub
Codespace. All commands assume you're in `/workspaces/medical`.

---

## 1. Start PostgreSQL

Postgres 16 is pre-installed in the Codespace. Start it and create the database:

```bash
# Start the cluster (may already be running)
sudo su - postgres -c "pg_ctlcluster 16 main start"

# Create user and database
sudo su - postgres -c "psql -c \"CREATE USER medvault WITH PASSWORD 'medvault';\""
sudo su - postgres -c "psql -c \"CREATE DATABASE medvault OWNER medvault;\""
sudo su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE medvault TO medvault;\""
```

Verify:
```bash
pg_isready -h localhost -p 5432
# → localhost:5432 - accepting connections
```

---

## 2. Backend setup

### Install dependencies

```bash
cd backend
pip install -e ".[dev]"
```

### Configure environment

Copy the template and edit if needed:

```bash
cp ../.env.example .env
```

The defaults work for local dev. Key values:

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://medvault:medvault@localhost:5432/medvault` | Must match the user/db created above |
| `JWT_SECRET_KEY` | `change-me-to-a-random-secret` | Any string; don't use this in production |
| `CORS_ORIGINS` | `https://<codespace-name>-5173.app.github.dev` | The forwarded frontend URL (see below) |

For the Codespace, set `CORS_ORIGINS` to the forwarded port-5173 URL:

```bash
# Find your codespace name
echo $CODESPACE_NAME
# Example: fictional-guide-jj5grwgvvr5cjjjq

# Set in .env:
CORS_ORIGINS=https://fictional-guide-jj5grwgvvr5cjjjq-5173.app.github.dev
```

### Run migrations

```bash
cd backend
alembic upgrade head
```

### Start the backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Make port 8000 public

In the Codespace **Ports** tab, find port 8000 and set its visibility to **Public**.
This is required so the frontend (on port 5173) can reach the API via the forwarded URL.

Verify: open `https://<codespace-name>-8000.app.github.dev/api/v1/health` in a browser.

---

## 3. Frontend setup

### Install dependencies

```bash
cd frontend
npm install
```

### Configure environment

```bash
cp .env.example .env
```

Set `VITE_API_BASE_URL` to the backend's forwarded URL (**no** `/api/v1` suffix, **no**
trailing slash):

```bash
# In frontend/.env:
VITE_API_BASE_URL=https://fictional-guide-jj5grwgvvr5cjjjq-8000.app.github.dev
```

### Start the frontend

```bash
npm run dev
```

Open the forwarded port-5173 URL in your browser:
`https://<codespace-name>-5173.app.github.dev`

---

## 4. Verify the stack

1. Open the frontend URL in your browser.
2. Click "Create one" to register a new account.
3. After registration, you'll be logged in and see the patient list (empty).
4. The backend health endpoint should return:
   ```
   GET /api/v1/health → {"status": "healthy", "service": "MedVault API"}
   ```

---

## 5. Run tests

```bash
# Backend (from backend/)
DATABASE_URL="postgresql+asyncpg://medvault:medvault@localhost:5432/medvault" python -m pytest tests/ -v

# Frontend (from frontend/)
npm test
```

---

## 6. Lint

```bash
# Backend
cd backend && ruff check app/ tests/ && black --check app/ tests/

# Frontend
cd frontend && npx eslint .
```

---

## Environment variable reference

### Backend (`.env` in repo root or `backend/`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://medvault:medvault@localhost:5432/medvault` | Async Postgres connection string |
| `JWT_SECRET_KEY` | Yes | `change-me-to-a-random-secret` | JWT signing key |
| `JWT_ALGORITHM` | No | `HS256` | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token lifetime |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime |
| `CORS_ORIGINS` | No | `""` (disabled) | Comma-separated allowed origins |
| `UPLOAD_DIR` | No | `./uploads` | Local file storage directory |
| `MAX_UPLOAD_SIZE_BYTES` | No | `10485760` (10 MB) | Max upload file size |
| `APP_NAME` | No | `MedVault` | Application name |
| `DEBUG` | No | `false` | Debug mode |

### Frontend (`frontend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | Backend base URL (no `/api/v1`, no trailing slash) |
