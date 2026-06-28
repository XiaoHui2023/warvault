#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  ./update.sh
fi
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pytest
