#!/usr/bin/env bash
# Run on the server which currently hosts africanappsstore.space.
set -euo pipefail
if [[ "${1:-}" == '--help' ]]; then
  echo 'Run as root on the public African Apps Store server. Publishes only the existing store and Kakakin release; no DNS changes.'
  exit 0
fi
[[ $# == 0 ]] || { echo 'No arguments expected.' >&2; exit 64; }
[[ ${EUID} == 0 ]] || { echo 'Run with sudo on the public African Apps Store host.' >&2; exit 77; }
# Check DNS before installing packages or updating any source files.
python3 - <<'PY'
import json,socket,subprocess,sys
addresses={x[4][0] for x in socket.getaddrinfo('africanappsstore.space',443,type=socket.SOCK_STREAM)}
interfaces=json.loads(subprocess.check_output(['ip','-j','address','show'],text=True))
local={a['local'] for i in interfaces for a in i.get('addr_info',[])}
if not addresses or not addresses.issubset(local):
 sys.exit('Wrong server: africanappsstore.space resolves to '+', '.join(sorted(addresses))+'. Connect to that store host and run this command there. DNS and local store files were not changed.')
print('Public store DNS matches this server.')
PY
if ! command -v git >/dev/null || ! command -v ansible-playbook >/dev/null || ! command -v flock >/dev/null; then
  apt-get update
  apt-get install -y git ansible-core ca-certificates util-linux
fi
exec 9>/run/lock/kakakin-store-publish.lock
flock -n 9 || { echo 'Another store publication is running.' >&2; exit 75; }
checkout=/opt/kakakin-store-release
export GIT_TERMINAL_PROMPT=0
if [[ ! -e "$checkout" ]]; then git clone https://github.com/olamidebello/africanappsstore.git "$checkout"; fi
[[ -d "$checkout/.git" && ! -L "$checkout" ]] || { echo 'Existing source path is not a regular Git checkout; preserved.' >&2; exit 73; }
[[ "$(git -C "$checkout" remote get-url origin)" == 'https://github.com/olamidebello/africanappsstore.git' ]] || { echo 'Unexpected repository origin; preserved.' >&2; exit 73; }
git -C "$checkout" diff --quiet && git -C "$checkout" diff --cached --quiet || { echo 'Local source edits found; preserved.' >&2; exit 73; }
git -C "$checkout" fetch origin main
git -C "$checkout" checkout --detach FETCH_HEAD
exec ansible-playbook -i 'localhost,' --connection local "$checkout/ansible/deploy-kakakin-mobile.yml"
