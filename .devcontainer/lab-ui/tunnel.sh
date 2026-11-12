#!/bin/bash
# Connects the lab app to its address on the site, when this codespace was opened from the site's "Open lab"
# button. Codespaces' own port forwarding only exists while the GitHub editor is open, so the site gives each
# codespace a Cloudflare tunnel instead.
#
# The codespace proves who it is with its own GITHUB_TOKEN (which only lets the launcher read who you are and
# this codespace's details) and gets back its tunnel's credential. A codespace opened any other way (the README's
# badge, VS Code, a laptop) gets "not opened from the site" and this does nothing.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# Always /tmp: XDG_RUNTIME_DIR differs between the dev container's start commands and a terminal.
RUN=/tmp/lab-ui
mkdir -p "$RUN" || { echo "lab app: can't make $RUN, so no tunnel"; exit 0; }
[ "${CODESPACES:-}" = true ] || exit 0
command -v cloudflared >/dev/null || exit 0
LAUNCHER="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("launcher", ""))' "$HERE/lab-ui.json")"
[ -n "$LAUNCHER" ] || exit 0

# Lifecycle commands don't always have GITHUB_TOKEN in their environment; Codespaces keeps it here too.
TOKEN="${GITHUB_TOKEN:-}"
SHARED=/workspaces/.codespaces/shared/user-secrets-envs.json
if [ -z "$TOKEN" ] && [ -r "$SHARED" ]; then
  TOKEN="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("GITHUB_TOKEN", ""))' "$SHARED")"
fi
[ -n "$TOKEN" ] || { echo "no GITHUB_TOKEN: the lab app stays on port 8000 only"; exit 0; }
NAME="${CODESPACE_NAME:-}"
if [ -z "$NAME" ] && [ -r "$SHARED" ]; then
  NAME="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("CODESPACE_NAME", ""))' "$SHARED")"
fi

# A few tries: on the very first start the site may still be setting the tunnel up.
for try in 1 2 3 4; do
  resp="$(curl -s --max-time 20 -w '\n%{http_code}' -X POST "$LAUNCHER/api/codespace-tunnel" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"codespace\": \"$NAME\"}")"
  code="${resp##*$'\n'}"
  body="${resp%$'\n'*}"
  [ "$code" = 200 ] && break
  sleep 10
done
if [ "$code" != 200 ]; then
  echo "lab app: not opened from the site, so no tunnel (port 8000 as usual)"
  exit 0
fi
read -r TUNNEL HOST < <(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["token"], d["host"])' <<<"$body")

pkill -f "cloudflared tunnel" 2>/dev/null || true
# The credential goes in through the environment, not the command line, so it doesn't show in `ps`.
TUNNEL_TOKEN="$TUNNEL" setsid nohup cloudflared tunnel --no-autoupdate --loglevel info run \
  > "$RUN/cloudflared.log" 2>&1 < /dev/null &
# make sure it's really up: say so if it isn't, instead of claiming an address that doesn't answer
for i in $(seq 1 20); do
  sleep 1
  grep -q "Registered tunnel connection" "$RUN/cloudflared.log" 2>/dev/null && { echo "lab app: https://$HOST/"; exit 0; }
  pgrep -x cloudflared >/dev/null || break
done
echo "lab app: the tunnel didn't connect. Its log, $RUN/cloudflared.log, ends:"
tail -5 "$RUN/cloudflared.log" 2>/dev/null | sed 's/^/  /'
