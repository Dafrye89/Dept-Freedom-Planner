#!/usr/bin/env sh
set -eu

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

python manage.py migrate
python manage.py bootstrap_superuser
python manage.py runserver 127.0.0.1:8000
