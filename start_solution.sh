#!/usr/bin/env bash
# =====================================================================
#  Telugu Document DB & API Solution — Startup Script
# =====================================================================

set -e

# Configuration
PROJECT_DIR="/home/surya/project/telugu_db_solution"
PG_BIN="/usr/lib/postgresql/17/bin"
PGDATA="/home/surya/data/pgdata"
DB_PORT=5433
API_PORT=8002
TUNNEL_KEY="$PROJECT_DIR/.serveo_key"

echo "=========================================================="
echo " Starting Telugu Document DB & API Solution..."
echo "=========================================================="

# 1. Ensure PostgreSQL personal cluster is running
if ! $PG_BIN/pg_isready -h "$PGDATA" -p $DB_PORT -q 2>/dev/null; then
    echo "[DB] Starting PostgreSQL personal cluster..."
    $PG_BIN/pg_ctl -D "$PGDATA" -l "$PGDATA/pg.log" -o "-p $DB_PORT -k $PGDATA" start
    sleep 2
else
    echo "[DB] PostgreSQL personal cluster already running on port $DB_PORT ✓"
fi

# 2. Verify Database connection & run setup
echo "[DB] Running schema script to ensure tables & indexes exist..."
PGPASSWORD="" psql -h "$PGDATA" -p $DB_PORT -U surya -d telugu_doc_db -f "$PROJECT_DIR/schema.sql" -q

# 3. Check if we need to load data (if documents table is empty)
DOC_COUNT=$(PGPASSWORD="" psql -h "$PGDATA" -p $DB_PORT -U surya -d telugu_doc_db -t -c "SELECT count(*) FROM documents;" | tr -d '[:space:]')
if [ "$DOC_COUNT" = "0" ]; then
    echo "[Data] Database is empty. Running db_loader..."
    python3 "$PROJECT_DIR/db_loader.py" --dir "/home/surya/project/auto"
else
    echo "[Data] Database already contains $DOC_COUNT documents ✓"
fi

# 4. Stop any existing FastAPI servers on API_PORT
echo "[API] Cleaning up any old API processes on port $API_PORT..."
PID=$(lsof -t -i:$API_PORT || true)
if [ -n "$PID" ]; then
    kill -9 $PID
    sleep 1
fi

# 5. Start FastAPI
echo "[API] Starting FastAPI server on port $API_PORT..."
cd "$PROJECT_DIR"
python3 -m uvicorn api.main:app --host 0.0.0.0 --port $API_PORT --log-level info > "$PROJECT_DIR/api_server.log" 2>&1 &
sleep 3

# 6. Establish public Serveo tunnel
echo "[Tunnel] Setting up public Serveo tunnel..."
if [ ! -f "$TUNNEL_KEY" ]; then
    ssh-keygen -t rsa -b 2048 -f "$TUNNEL_KEY" -N "" -q
fi

# Kill old ssh tunnels
pkill -f "serveo.net" || true

# Run SSH in the background and output to tunnel.log to find URL
ssh -i "$TUNNEL_KEY" \
    -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 \
    -R 80:localhost:$API_PORT \
    serveo.net > "$PROJECT_DIR/tunnel.log" 2>&1 &

echo "[Tunnel] Waiting for public URL..."
sleep 5

# Extract the public URL from the tunnel log
PUBLIC_URL=""
for i in {1..6}; do
    if grep -o "https://[a-zA-Z0-9.-]*\.serveo\.net" "$PROJECT_DIR/tunnel.log" >/dev/null; then
        PUBLIC_URL=$(grep -o "https://[a-zA-Z0-9.-]*\.serveo\.net" "$PROJECT_DIR/tunnel.log" | head -n 1)
        break
    fi
    sleep 2
done

echo ""
echo "=========================================================="
echo "  Telugu DB & API Solution is Live!"
echo "=========================================================="
echo "  Local Dashboard : http://127.0.0.1:$API_PORT"
echo "  Swagger API Docs: http://127.0.0.1:$API_PORT/docs"
if [ -n "$PUBLIC_URL" ]; then
    echo "  Public Live URL : $PUBLIC_URL"
else
    echo "  Public Live URL : (Check $PROJECT_DIR/tunnel.log for URL)"
fi
echo "=========================================================="
echo "Logs are available at: "
echo "  - API server: $PROJECT_DIR/api_server.log"
echo "  - SSH Tunnel: $PROJECT_DIR/tunnel.log"
echo "=========================================================="
