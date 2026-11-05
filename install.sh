#!/usr/bin/env bash
# Minegrub-style entry point; default is a read-only installation plan.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 "$SCRIPT_DIR/scripts/manage-install.py" install "$@"
