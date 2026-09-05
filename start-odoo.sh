#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/omer/src/odoo/19.0"
exec "$ROOT/venv/bin/python" "$ROOT/odoo/odoo-bin" -c "$ROOT/odoo.conf" "$@"
