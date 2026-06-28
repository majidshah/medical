#!/usr/bin/env bash
# MedVault — one-command Codespace dev setup
# Safe to run at the start of every session. Idempotent.
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${BOLD}🏥 MedVault dev-start${NC}"
echo ""

# ── 1. Start PostgreSQL ──────────────────────────────────────────────
echo -e "${GREEN}▸ Starting PostgreSQL...${NC}"
if pg_isready -h localhost -p 5432 -q 2>/dev/null; then
  echo "  Already running."
else
  sudo su - postgres -c "pg_ctlcluster 16 main start" 2>/dev/null \
    || sudo pg_ctlcluster 16 main start 2>/dev/null \
    || echo "  ⚠ Could not start — check pg_lsclusters"
  sleep 1
fi

# ── 2. Ensure medvault role + database ───────────────────────────────
echo -e "${GREEN}▸ Ensuring medvault user and database...${NC}"
sudo su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='medvault'\" | grep -q 1" 2>/dev/null \
  && echo "  User exists." \
  || { sudo su - postgres -c "psql -c \"CREATE USER medvault WITH PASSWORD 'medvault';\""; echo "  User created."; }

sudo su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='medvault'\" | grep -q 1" 2>/dev/null \
  && echo "  Database exists." \
  || { sudo su - postgres -c "psql -c \"CREATE DATABASE medvault OWNER medvault;\""; echo "  Database created."; }

# Password is synced from .env in step 3 (single source of truth)

# ── 3. Backend .env (single source of truth for DB password) ─────────
echo -e "${GREEN}▸ Checking backend .env...${NC}"
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "  Created backend/.env from template."
else
  echo "  Already exists."
fi

# Read the DB password from .env's DATABASE_URL so the script always agrees
DB_URL=$(grep -E '^DATABASE_URL=' backend/.env | head -1 | cut -d= -f2-)
DB_PASS=$(echo "$DB_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
DB_PASS=${DB_PASS:-medvault}

# Set the Postgres user password to match .env (single source of truth)
sudo su - postgres -c "psql -c \"ALTER USER medvault WITH PASSWORD '${DB_PASS}';\"" >/dev/null 2>&1
echo "  DB password synced from .env."

# ── 4. Install backend deps (if needed) ─────────────────────────────
echo -e "${GREEN}▸ Installing backend dependencies...${NC}"
cd /workspaces/medical/backend
pip install -e ".[dev]" -q 2>&1 | tail -1

# ── 5. Run Alembic migrations ────────────────────────────────────────
echo -e "${GREEN}▸ Running Alembic migrations...${NC}"
DATABASE_URL="${DB_URL}" \
  alembic upgrade head 2>&1 | grep -E "Running upgrade|already" || true
echo "  Migrations complete."

# ── 6. Install frontend deps (if needed) ─────────────────────────────
echo -e "${GREEN}▸ Installing frontend dependencies...${NC}"
cd /workspaces/medical/frontend
if [ ! -d node_modules ]; then
  npm install --silent 2>&1 | tail -1
  echo "  Installed."
else
  echo "  Already installed."
fi

# ── 7. Frontend .env ─────────────────────────────────────────────────
echo -e "${GREEN}▸ Checking frontend .env...${NC}"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  Created frontend/.env from template."
else
  echo "  Already exists."
fi

cd /workspaces/medical

# ── 8. Print reminders ───────────────────────────────────────────────
CODESPACE=${CODESPACE_NAME:-"your-codespace-name"}
echo ""
echo -e "${BOLD}━━━ Setup complete ━━━${NC}"
echo ""
echo -e "${YELLOW}Before starting the servers, set these env values:${NC}"
echo ""
echo "  Backend (.env or shell):"
echo "    CORS_ORIGINS=https://${CODESPACE}-5173.app.github.dev"
echo ""
echo "  Frontend (frontend/.env):"
echo "    VITE_API_BASE_URL=https://${CODESPACE}-8000.app.github.dev"
echo ""
echo -e "${YELLOW}Make port 8000 PUBLIC in the Codespace Ports tab.${NC}"
echo ""
echo "  Start backend:  cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo "  Start frontend: cd frontend && npm run dev"
echo ""
echo -e "${GREEN}Open: https://${CODESPACE}-5173.app.github.dev${NC}"
