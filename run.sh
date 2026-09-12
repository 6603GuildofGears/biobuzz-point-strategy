#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m biobuzz simulate --matches "${1:-4000}" --out output
echo "Open output/report.html"
