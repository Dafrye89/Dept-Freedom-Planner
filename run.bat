@echo off
setlocal

if not exist .venv (
  py -3 -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
  copy .env.example .env >nul
)

python manage.py migrate
python manage.py bootstrap_superuser
python manage.py runserver 127.0.0.1:8000
