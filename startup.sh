#!/usr/bin/env bash
set -euo pipefail

if [[ -f "/home/site/wwwroot/manage.py" ]]; then
  cd /home/site/wwwroot
else
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  cd "$SCRIPT_DIR"
fi

if ! python -c "import reportlab" >/dev/null 2>&1; then
  echo "Installing missing Python dependencies..."
  python -m pip install -r requirements.txt
fi

python manage.py migrate --noinput
python manage.py bootstrap_superuser
if [[ -n "${STRIPE_SECRET_KEY:-}" && -n "${STRIPE_PRO_PRICE_ID:-}" ]]; then
  echo "Running Stripe access reconciliation..."
  if ! python manage.py reconcile_stripe_access --all; then
    echo "Stripe reconciliation failed during startup; continuing app boot."
  fi
fi
python manage.py collectstatic --noinput

exec waitress-serve --listen="0.0.0.0:${PORT:-8000}" config.wsgi:application
