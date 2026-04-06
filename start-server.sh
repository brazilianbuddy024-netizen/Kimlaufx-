#!/bin/bash
cd /home/z/my-project
# Kill any leftover processes on port 3000
fuser -k 3000/tcp 2>/dev/null
sleep 1
# Start watchdog which auto-restarts the production server
node watchdog.cjs &
