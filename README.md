# Debt Freedom Planner

Debt Freedom Planner is a full Django application for building plain-language debt payoff plans. It is designed for older users who want a calm, patriotic, easy-to-follow experience without spreadsheets, bank connections, or finance jargon.

## Stack

- Django 5
- SQLite for local development
- Django templates with HTMX, Alpine.js, and a compiled Tailwind CSS design system
- `django-allauth` for email/password auth and Google SSO wiring
- WhiteNoise for static files
- WeasyPrint with an `xhtml2pdf` fallback for PDF export on Windows
- Playwright for browser QA

## Core features

- Anonymous calculator with snowball, avalanche, and custom payoff order
- Guided 3-step planner flow
- Free tier with one saved plan and print view
- Paid tier with unlimited saved plans, unlimited custom scenarios, and PDF export
- Founder override for `dafrye89`, including premium access and the only visible admin link
- Django admin at `/control-room/`

## Local setup

### Windows

```powershell
.\run.bat
```

### Linux / macOS

```bash
chmod +x run.sh
./run.sh
```

The startup script will:

- create `.venv` if needed
- install `requirements.txt`
- copy `.env.example` to `.env` if needed
- run migrations
- bootstrap the founder superuser
- start Django on `http://127.0.0.1:8000/`

## Founder bootstrap

The local bootstrap command creates the founder superuser defined in `.env`:

- username: `dafrye89`
- password: `DafHef_04!`

## Tests

Run the Django test suite:

```powershell
.\.venv\Scripts\pytest
```

Run browser QA and screenshots:

```powershell
npm install
npm run build:css
npm run qa:playwright
```

Use the Tailwind watcher while editing the UI:

```powershell
npm run watch:css
```

Playwright screenshots are written to `output/playwright/`.

## Environment

Copy `.env.example` to `.env` and update values as needed. Important local values include:

- `DEBUG`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `BOOTSTRAP_SUPERUSER_USERNAME`
- `BOOTSTRAP_SUPERUSER_PASSWORD`
- `BOOTSTRAP_SUPERUSER_EMAIL`

## Project structure

- `config/`: Django settings, URLs, WSGI/ASGI
- `accounts/`: custom user model, access policy, founder bootstrap
- `core/`: landing page, guided planner flow, draft session logic, event logging
- `plans/`: saved plan CRUD and scenario management
- `calculator/`: pure Python payoff engine
- `exports/`: printable view and PDF export
- `billing/`: pricing and paid-tier messaging
- `legal/`: privacy, terms, and disclaimer pages
- `tests/`: Django tests and Playwright smoke QA

## Notes

- Google login is wired through `django-allauth` and only appears when Google credentials are set.
- The older mockup and marketing assets remain in the repo as references and are not the runtime app.
