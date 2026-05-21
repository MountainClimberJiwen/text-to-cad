#!/bin/zsh

set -u

APP_LABEL="com.jiwen.freecad-assembler-viewer"
NGROK_LABEL="com.jiwen.ngrok-3000"

echo "== LaunchAgents =="
launchctl print "gui/$(id -u)/$APP_LABEL" 2>/dev/null | sed -n '1,20p'
echo
launchctl print "gui/$(id -u)/$NGROK_LABEL" 2>/dev/null | sed -n '1,20p'
echo

echo "== Local Health =="
curl -s http://127.0.0.1:3000/api/health || echo "http://127.0.0.1:3000 unreachable"
echo
echo

echo "== Ngrok Tunnel =="
curl -s http://127.0.0.1:4040/api/tunnels || echo "http://127.0.0.1:4040 unreachable"
echo
