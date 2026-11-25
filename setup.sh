#!/usr/bin/env bash
# One-time setup: installs the Python packages, downloads the OFL fonts and checks the engine.
#   ./setup.sh          everything
#   ./setup.sh --deps   only the Python packages
#   ./setup.sh --fonts  only the fonts
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
say() { printf '%s\n' "$*"; }
cd "$HERE"

do_deps() {
  if command -v uv >/dev/null 2>&1; then
    say "installing Python packages with uv ..."
    uv sync --project "$HERE" --quiet
  else
    say "installing Python packages with venv + pip ..."
    command -v python3 >/dev/null 2>&1 || { say "Python 3.10+ is required: https://www.python.org/downloads/"; exit 1; }
    [ -d ".venv" ] || python3 -m venv .venv
    .venv/bin/python -m pip install --upgrade pip --quiet
    .venv/bin/python -m pip install --quiet -r requirements.txt
  fi
}

case "${1:-}" in
  --deps)  do_deps ;;
  --fonts) ./ccb fonts ;;
  *)
    do_deps
    say ""
    say "downloading the fonts (about 6 MB, SIL Open Font License) ..."
    ./ccb fonts || say "note: fonts could not be downloaded; the engine will use a system font"
    say ""
    ./ccb doctor
    say ""
    say "Ready. Try it with the demo photographs:"
    say "  ./ccb samples"
    say "  ./ccb make inputs/*.jpg --name demo"
    say ""
    say "Face detection (optional, one 340 KB model):"
    say "  ./ccb faces"
    say ""
    say "In OpenCode, run 'opencode' in this folder, pick a model, and type: /card inputs/"
    ;;
esac
