#!/usr/bin/env bash
# Run the three demo flows against the LIVE Otari gateway and save the
# terminal output used in the demo video. Requires OTARI_API_KEY (or .env).
set -u
cd "$(dirname "$0")/.."
mkdir -p demo/captures

run() {
  name="$1"; shift
  echo "\$ askall $*" > "demo/captures/$name.txt"
  python3 -m askall.cli "$@" >> "demo/captures/$name.txt" 2>&1
  echo "--- $name done (exit $?) ---"
}

run models   models
run panel    panel "Should a small startup build its own login system or use an auth provider? Answer briefly."
run research research "What were the headline announcements at MozFest 2026 this week?"
run calc     calc "If I put aside 250 dollars a month at a 7 percent annual return, compounded monthly, what is it worth after 20 years?"
echo "Captures in demo/captures/"
