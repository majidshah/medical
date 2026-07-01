#!/usr/bin/env bash
# MedVault — one-command Codespace setup + start
# Idempotent: safe to run at the start of every session, after a rebuild,
# or whenever things look broken. Starts both servers before exiting.
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

ROOT=/workspaces/medical
BACKEND_LOG=/tmp/medvault-backend.log
FRONTEND_LOG=/tmp/medvault-frontend.log

echo -e "${BOLD}▸ MedVault dev-start${NC}"
echo ""

# ── helper: update key=value in a .env file when the current value is
#   absent, localhost/127.x, or any .app.github.dev URL (stale codespace).
#   Intentionally-set custom values (e.g. a real domain) are never touched.
update_env_if_local_or_stale() {
  local file="$1" key="$2" new_val="$3"
  local current
  current=$(grep -E "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- || true)
  if [ -z "$current" ] \
      || echo "$current" | grep -qE '^https?://localhost' \
      || echo "$current" | grep -qE '^https?://127\.' \
      || echo "$current" | grep -q 'app\.github\.dev'; then
    if grep -q "^${key}=" "$file" 2>/dev/null; then
      sed -i "s|^${key}=.*|${key}=${new_val}|" "$file"
    else
      printf '\n%s=%s\n' "$key" "$new_val" >> "$file"
    fi
    echo "  ✓ ${key} → ${new_val}"
  else
    echo "  ${key} is custom (${current}) — kept."
  fi
}

# ── 1. PostgreSQL ────────────────────────────────────────────────────
echo -e "${GREEN}▸ Starting PostgreSQL...${NC}"
if pg_isready -h localhost -p 5432 -q 2>/dev/null; then
  echo "  Already running."
else
  sudo su - postgres -c "pg_ctlcluster 16 main start" 2>/dev/null \
    || sudo pg_ctlcluster 16 main start 2>/dev/null \
    || echo "  ⚠ Could not start — check pg_lsclusters"
  sleep 1
fi

# ── 2. medvault role + database ──────────────────────────────────────
echo -e "${GREEN}▸ Ensuring medvault user and database...${NC}"
if sudo su - postgres -c \
    "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='medvault'\" | grep -q 1" \
    2>/dev/null; then
  echo "  User exists."
else
  sudo su - postgres -c \
    "psql -c \"CREATE USER medvault WITH PASSWORD 'medvault';\"" >/dev/null
  echo "  User created."
fi

if sudo su - postgres -c \
    "psql -tc \"SELECT 1 FROM pg_database WHERE datname='medvault'\" | grep -q 1" \
    2>/dev/null; then
  echo "  Database exists."
else
  sudo su - postgres -c \
    "psql -c \"CREATE DATABASE medvault OWNER medvault;\"" >/dev/null
  echo "  Database created."
fi

# ── 3. Backend .env — create if missing, sync DB password ────────────
echo -e "${GREEN}▸ Checking backend .env...${NC}"
if [ ! -f "${ROOT}/backend/.env" ]; then
  cp "${ROOT}/backend/.env.example" "${ROOT}/backend/.env"
  echo "  Created from template."
else
  echo "  Already exists."
fi

DB_URL=$(grep -E '^DATABASE_URL=' "${ROOT}/backend/.env" | head -1 | cut -d= -f2-)
DB_URL=${DB_URL:-postgresql+asyncpg://medvault:medvault@localhost:5432/medvault}
DB_PASS=$(echo "$DB_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
DB_PASS=${DB_PASS:-medvault}

sudo su - postgres -c \
  "psql -c \"ALTER USER medvault WITH PASSWORD '${DB_PASS}';\"" >/dev/null 2>&1
echo "  DB password synced from .env."

# ── 4. Backend deps ──────────────────────────────────────────────────
echo -e "${GREEN}▸ Installing backend dependencies...${NC}"
cd "${ROOT}/backend"
pip install -e ".[dev]" -q 2>&1 | tail -1 || true

# ── 5. Alembic migrations + schema verification ──────────────────────
echo -e "${GREEN}▸ Running Alembic migrations...${NC}"
DATABASE_URL="${DB_URL}" alembic upgrade head 2>&1 | grep -E "Running upgrade|already" || true

# Verify core tables exist — if missing despite "head" (e.g. schema was
# dropped externally), wipe and rebuild from scratch.
if ! PGPASSWORD="${DB_PASS}" psql -h localhost -U medvault -d medvault \
    -tc "SELECT 1 FROM information_schema.tables WHERE table_name='accounts'" \
    2>/dev/null | grep -q 1; then
  echo "  ⚠ accounts table missing — dropping schema and rebuilding..."
  PGPASSWORD="${DB_PASS}" psql -h localhost -U medvault -d medvault \
    -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" >/dev/null 2>&1 || true
  DATABASE_URL="${DB_URL}" alembic stamp base >/dev/null 2>&1
  DATABASE_URL="${DB_URL}" alembic upgrade head 2>&1 | grep -E "Running upgrade" || true
fi
echo "  Migrations OK."

# ── 6. Frontend deps ─────────────────────────────────────────────────
echo -e "${GREEN}▸ Installing frontend dependencies...${NC}"
cd "${ROOT}/frontend"
if [ ! -d node_modules ]; then
  npm install --silent 2>&1 | tail -1
  echo "  Installed."
else
  echo "  Already installed."
fi
cd "${ROOT}"

# ── 7. Write Codespace URLs into env files ────────────────────────────
echo -e "${GREEN}▸ Configuring env URLs...${NC}"
if [ ! -f "${ROOT}/frontend/.env" ]; then
  cp "${ROOT}/frontend/.env.example" "${ROOT}/frontend/.env"
  echo "  Created frontend/.env from template."
fi

if [ -n "${CODESPACE_NAME:-}" ]; then
  BACKEND_URL="https://${CODESPACE_NAME}-8000.app.github.dev"
  FRONTEND_URL="https://${CODESPACE_NAME}-5173.app.github.dev"
  update_env_if_local_or_stale "${ROOT}/frontend/.env" "VITE_API_BASE_URL" "${BACKEND_URL}"
  update_env_if_local_or_stale "${ROOT}/backend/.env"  "CORS_ORIGINS"      "${FRONTEND_URL}"
else
  BACKEND_URL="http://localhost:8000"
  FRONTEND_URL="http://localhost:5173"
  echo "  CODESPACE_NAME not set — using localhost defaults."
fi

# ── 8. Make Codespace ports public ───────────────────────────────────
echo -e "${GREEN}▸ Setting port visibility...${NC}"
if [ -n "${CODESPACE_NAME:-}" ]; then
  if command -v gh &>/dev/null; then
    if gh codespace ports visibility 8000:public 5173:public \
        -c "${CODESPACE_NAME}" 2>&1; then
      echo "  Ports 8000 + 5173 set to public."
    else
      echo -e "  ${YELLOW}⚠ gh ports command failed — set ports Public in the Ports tab.${NC}"
    fi
  else
    echo -e "  ${YELLOW}⚠ gh CLI not found. Run manually:${NC}"
    echo "    gh codespace ports visibility 8000:public 5173:public -c ${CODESPACE_NAME}"
  fi
else
  echo "  Local dev — port visibility not applicable."
fi

# ── 9. Kill stale processes on 5173 and 8000 ─────────────────────────
echo -e "${GREEN}▸ Clearing ports 5173 and 8000...${NC}"
for port in 8000 5173; do
  pids=$(lsof -ti:"${port}" -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "$pids" | xargs -r kill 2>/dev/null || true
    sleep 0.5
    echo "  Killed stale process(es) on :${port}."
  else
    echo "  :${port} is free."
  fi
done

# ── 10. Start backend ─────────────────────────────────────────────────
echo -e "${GREEN}▸ Starting backend (uvicorn :8000)...${NC}"
cd "${ROOT}/backend"
DATABASE_URL="${DB_URL}" \
  nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 \
  > "${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!
echo "  PID ${BACKEND_PID} — logs: ${BACKEND_LOG}"

# ── 11. Start frontend ────────────────────────────────────────────────
echo -e "${GREEN}▸ Starting frontend (vite :5173)...${NC}"
cd "${ROOT}/frontend"
nohup npm run dev > "${FRONTEND_LOG}" 2>&1 &
FRONTEND_PID=$!
echo "  PID ${FRONTEND_PID} — logs: ${FRONTEND_LOG}"

cd "${ROOT}"

# ── 12. Wait for both servers to respond (up to 30 s) ─────────────────
echo -e "${GREEN}▸ Waiting for servers...${NC}"
BE_UP=0
FE_UP=0
for i in $(seq 1 30); do
  sleep 1
  if [ "$BE_UP" -eq 0 ] && curl -sf http://localhost:8000/api/v1/health >/dev/null 2>&1; then
    BE_UP=1
    echo "  ✓ Backend responding."
  fi
  if [ "$FE_UP" -eq 0 ] && lsof -ti:5173 -sTCP:LISTEN >/dev/null 2>&1; then
    FE_UP=1
    echo "  ✓ Frontend listening."
  fi
  if [ "$BE_UP" -eq 1 ] && [ "$FE_UP" -eq 1 ]; then
    break
  fi
  if [ "$((i % 5))" -eq 0 ]; then
    printf "  still waiting... (%d/30s)\n" "$i"
  fi
done

if [ "$BE_UP" -eq 0 ]; then
  echo -e "  ${RED}✗ Backend not responding — check: tail ${BACKEND_LOG}${NC}"
fi
if [ "$FE_UP" -eq 0 ]; then
  echo -e "  ${RED}✗ Frontend not listening — check: tail ${FRONTEND_LOG}${NC}"
fi

# ── 13. DB status ─────────────────────────────────────────────────────
ACCOUNT_COUNT=$(PGPASSWORD="${DB_PASS}" psql -h localhost -U medvault -d medvault \
  -tc "SELECT COUNT(*) FROM accounts" 2>/dev/null | tr -d ' \n' || echo "?")

# ── 14. Summary ───────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${BOLD}Open:${NC}  ${FRONTEND_URL}"
echo -e "  ${BOLD}API:${NC}   ${BACKEND_URL}/api/v1/health"
echo ""
if [ "$ACCOUNT_COUNT" = "0" ]; then
  echo -e "  ${YELLOW}DB is empty — register a new account to get started.${NC}"
elif [ "$ACCOUNT_COUNT" = "?" ]; then
  echo -e "  ${YELLOW}Could not query account count — check DB connectivity.${NC}"
else
  echo -e "  ${GREEN}DB has ${ACCOUNT_COUNT} account(s) — log in or register.${NC}"
fi
echo ""
echo "  Logs:  tail -f ${BACKEND_LOG}"
echo "         tail -f ${FRONTEND_LOG}"
echo "  Stop:  kill ${BACKEND_PID} ${FRONTEND_PID}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
