#!/usr/bin/env bash
# =====================================================================
#  Persistent SSH Tunnel Keep-Alive Script
# =====================================================================

TUNNEL_KEY="/home/surya/project/telugu_db_solution/.serveo_key"
API_PORT=8002
LOG_FILE="/home/surya/project/telugu_db_solution/tunnel.log"

# Clean up any existing serveo tunnels
pkill -f "serveo.net" || true

echo "=== Starting Tunnel Keep-Alive Daemon ==="
echo "Logging to $LOG_FILE"

# Empty the log file
> "$LOG_FILE"

while true; do
    echo "[$(date)] Launching ssh tunnel to serveo.net..." >> "$LOG_FILE"
    
    ssh -i "$TUNNEL_KEY" \
        -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=15 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -R 80:localhost:$API_PORT \
        serveo.net >> "$LOG_FILE" 2>&1
    
    echo "[$(date)] SSH exited. Reconnecting in 3 seconds..." >> "$LOG_FILE"
    sleep 3
done
