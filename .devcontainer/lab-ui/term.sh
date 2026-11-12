#!/bin/bash
# What the web terminal runs: a shell on one of the lab's nodes, the same as `make shell H=<node>`.
# The node's name comes from the page's address (/term/?arg=laptop), so only the Topology tab's nodes are allowed.
HERE="$(cd "$(dirname "$0")" && pwd)"
NODE="${1:-}"
python3 -c 'import json,sys; t=json.load(open(sys.argv[1])).get("topology") or {}; sys.exit(sys.argv[2] not in [n["id"] for n in t.get("nodes", []) if n.get("shell", True)])' \
  "$HERE/lab-ui.json" "$NODE" || { echo "no node called '$NODE' in this lab"; exit 1; }
cd "$HERE/../.."
until docker ps --format '{{.Names}}' | grep -qx "$NODE"; do
  echo "$NODE isn't running yet: waiting for the network to come up ..."
  sleep 5
done
exec make -s shell H="$NODE"
