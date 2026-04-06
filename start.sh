#!/bin/bash
while true; do
  cd /home/z/my-project
  node .next/standalone/server.js --port 3000 2>/tmp/server.log
  sleep 0.5
done
