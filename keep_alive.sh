#!/bin/bash
# Auto-restart wrapper — if the sandbox kills the server, restart it immediately.
# This ensures port 3000 always has a listener.
while true; do
    python3 /home/z/my-project/server.py 2>&1
    echo "[KeepAlive] Server died, restarting in 0.5s..." >&2
    sleep 0.5
done
