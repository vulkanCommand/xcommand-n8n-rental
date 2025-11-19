#!/usr/bin/env bash
set -euo pipefail
if [ $# -ne 1 ]; then
  echo "usage: ws <u-xxxxxx>" >&2
  exit 1
fi
SUB="$1"

# Find container by label (preferred), else by name
CID=$(docker ps -aq --filter "label=com.xcommand.sub=$SUB")
if [ -z "$CID" ] && docker ps -a --format '{{.Names}}' | grep -q "^n8n_${SUB}\$"; then
  CID=$(docker ps -aq -f "name=^n8n_${SUB}\$")
fi

if [ -z "$CID" ]; then
  echo "workspace not found for $SUB" >&2
  exit 2
fi

docker inspect -f \
'{{.Name}}  sub={{ index .Config.Labels "com.xcommand.sub"}}  exp={{ index .Config.Labels "com.xcommand.expires_at"}}  url=http://localhost:{{ (index (index .NetworkSettings.Ports "5678/tcp") 0).HostPort }}  status={{.State.Status}}' \
"$CID"
