#!/bin/bash
# Starts the lab app: Caddy on port 8000 (the page, and every tab behind one address) and its API on 8001.
# The dev container runs this first, before anything else is set up, so the app is up in a second and shows
# the rest of the start (the images, the network) as it happens. It runs again on every start: if the app is
# already answering it leaves it alone. --restart restarts it anyway (after changing lab-ui.json).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# Always /tmp: XDG_RUNTIME_DIR differs between the dev container's start commands and a terminal.
RUN=/tmp/lab-ui
answering() { curl -fs -o /dev/null --max-time 2 http://127.0.0.1:8000/api/status; }
if [ "${1:-}" != "--restart" ] && answering; then
  echo "lab app already on port 8000"
  exit 0
fi
mkdir -p "$RUN"
python3 "$HERE/server.py" --caddyfile > "$RUN/Caddyfile"
pkill -f "lab-ui/server.py" 2>/dev/null || true
pkill -x caddy 2>/dev/null || true
pkill -x ttyd 2>/dev/null || true
# setsid + nohup: both keep running after the dev container's start command returns.
setsid nohup python3 "$HERE/server.py" > "$RUN/api.log" 2>&1 < /dev/null &
setsid nohup caddy run --config "$RUN/Caddyfile" --adapter caddyfile > "$RUN/caddy.log" 2>&1 < /dev/null &
# The web terminal behind the Topology tab: /term/?arg=<node> opens a shell on that node (term.sh checks the name).
TERM_PORT="$(python3 "$HERE/server.py" --terminal)"
if [ -n "$TERM_PORT" ] && command -v ttyd >/dev/null; then
  setsid nohup ttyd --interface 127.0.0.1 --port "$TERM_PORT" --base-path /term --writable --url-arg \
    --client-option disableLeaveAlert=true --client-option fontSize=14 \
    --client-option 'theme={"background":"#040a14","foreground":"#c4e3f0","cursor":"#3ad7ff","selectionBackground":"#24496b"}' \
    bash "$HERE/term.sh" > "$RUN/ttyd.log" 2>&1 < /dev/null &
fi
for i in $(seq 1 20); do
  answering && { echo "lab app on port 8000"; exit 0; }
  sleep 0.5
done
echo "the lab app didn't start: see $RUN/caddy.log and $RUN/api.log" >&2
exit 1
