Below is a **complete recommended stack and implementation outline** for the Debt Payoff Tool, filled in with the parts people usually forget.

# Project overview

**Project name:** Debt Freedom Planner
**App type:** Django web app
**Purpose:** Let users enter debts, choose a payoff strategy, view a payoff timeline, compare scenarios, save plans, and export printable summaries.

This should be built as a **simple, trustworthy web app**, not a complicated fintech platform.

---

# 1. Recommended stack

## Core application stack

* **Backend framework:** Django
* **Language:** Python 3.12
* **Database for local/dev and early prod:** SQLite
* **Frontend rendering:** Django templates
* **Frontend interactivity:** HTMX + Alpine.js
* **Styling:** Bootstrap 5 or simple custom CSS
* **Authentication:** Django auth
* **SSO:** Google OAuth via `django-allauth`
* **Email/password auth:** yes
* **Background tasks:** optional later with Celery
* **PDF generation:** WeasyPrint
* **Charts:** Chart.js
* **Environment management:** Python `venv`
* **Dependency file:** `requirements.txt`
* **Windows startup:** `run.bat`
* **Linux/macOS startup:** `run.sh`
* **Config management:** `.env`
* **Static file serving in simple deployment:** WhiteNoise
* **Production web server:** Gunicorn on Linux or Waitress on Windows
* **Reverse proxy in production:** Nginx or Caddy
* **Version control:** Git
* **Migrations:** Django migrations
* **Admin panel:** Django admin
* **Forms:** Django forms or ModelForms
* **Testing:** Django test framework + pytest optional
* **Linting/formatting:** Black, Ruff
* **Logging:** Python logging to file + console
* **Monitoring later:** Sentry optional

---

# 2. Why this stack

## Why Django

Django gives you:

* auth
* admin
* forms
* ORM
* migrations
* session handling
* CSRF protection
* templating

That means fewer moving parts and faster development.

## Why SQLite first

For MVP and early users, SQLite is fine if:

* traffic is moderate
* app logic is simple
* you want very fast setup

Later you can move to PostgreSQL if needed.

## Why Django templates + HTMX

This avoids overengineering with React while still allowing:

* inline updates
* partial refreshes
* cleaner UX

It is a great fit for:

* forms
* calculators
* dashboards
* tables
* printable layouts

## Why venv instead of conda

For a normal Django SaaS app:

* `venv` is lighter
* easier for most Python web devs
* simpler deploy story
* fewer unnecessary moving parts

Use conda only if the project depends on unusual scientific packages. This one does not.

---

# 3. Project architecture

## Main app modules

Recommended Django apps:

* `core`
  shared utilities, homepage, settings helpers

* `accounts`
  auth, profile, Google login config, account preferences

* `plans`
  debt plans, debt items, scenario setup

* `calculator`
  payoff engine, schedule generation, comparison logic

* `exports`
  PDF export, print view, downloadable summaries

* `analytics_app`
  app events, conversions, funnel tracking

* `legal`
  privacy policy, terms, disclaimers

* `billing`
  Stripe or other billing later

---

# 4. Full folder structure

A good starting structure:

```text
debt_freedom_planner/
│
├── manage.py
├── run.bat
├── run.sh
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── CHANGELOG.md
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── core/
├── accounts/
├── plans/
├── calculator/
├── exports/
├── analytics_app/
├── legal/
├── billing/
│
├── templates/
│   ├── base.html
│   ├── components/
│   ├── core/
│   ├── accounts/
│   ├── plans/
│   ├── calculator/
│   ├── exports/
│   └── legal/
│
├── static/
│   ├── css/
│   ├── js/
│   ├── img/
│   └── vendor/
│
├── media/
│
├── logs/
│
└── tests/
```

---

# 5. Authentication setup

## Required auth methods

Support both:

* email/password
* Google SSO

## Recommended package

* `django-allauth`

## Auth requirements

* register with email
* login with email
* forgot password flow
* verify email address
* Google login button
* logout
* account settings page

## Notes

If Google OAuth setup is delayed, the app should still fully work with email/password only.

---

# 6. Database design

## User

Use Django’s built-in user model, but strongly consider a custom user model from day one.

Fields:

* email as primary login field
* first_name optional
* last_name optional
* created_at
* updated_at

## Profile

Optional separate profile model:

* user
* display_name
* timezone
* marketing_opt_in
* created_at
* updated_at

## DebtPlan

Fields:

* id
* user FK nullable for guest/temporary mode if supported
* title
* strategy_type (`snowball`, `avalanche`, `custom`)
* extra_monthly_payment
* total_balance_snapshot
* projected_payoff_date
* projected_months_to_payoff
* projected_total_interest
* projected_total_paid
* created_at
* updated_at
* is_archived

## DebtItem

Fields:

* id
* debt_plan FK
* name
* lender_name nullable
* balance
* apr
* minimum_payment
* due_day nullable
* notes nullable
* custom_order nullable
* created_at
* updated_at

## ScenarioComparison

Optional but helpful:

* debt_plan FK
* scenario_name
* strategy_type
* extra_monthly_payment
* payoff_date
* months_to_payoff
* total_interest
* total_paid
* created_at

## EventLog

For funnel tracking:

* event_name
* user nullable
* session_key nullable
* metadata JSON
* created_at

---

# 7. Core calculation engine

This should be isolated in pure Python code so it is easy to:

* test
* reuse
* call from views
* later expose through API if needed

## Suggested location

`calculator/services/payoff_engine.py`

## Inputs

* list of debt items
* payoff strategy
* extra monthly payment
* optional simulation start date

## Outputs

* debt-free date
* months to payoff
* total interest
* total paid
* payoff order
* full amortization schedule
* yearly summary
* comparison summary

## Important

Do not bury calculation logic inside Django views.

---

# 8. Frontend stack details

## Templating

* Django templates for server-rendered pages

## CSS framework

Best options:

* Bootstrap 5 for speed
* or custom CSS if you want tighter branding

For MVP, Bootstrap is fine.

## JS

* HTMX for partial form submits and result refreshes
* Alpine.js for light client-side interactions
* Chart.js for results graphs

## UI needs

* large readable form fields
* obvious CTA buttons
* mobile-friendly layout
* printable summary screen
* accessible contrast
* simple wording

---

# 9. Pages/screens required

## Public pages

* homepage
* features
* pricing
* FAQ
* privacy policy
* terms
* disclaimer
* login
* signup
* forgot password

## App pages

* dashboard
* create plan
* edit plan
* strategy selection
* results summary
* full payoff schedule
* comparison view
* export/print page
* account settings

## Admin pages

* users
* plans
* debt items
* event logs
* billing status later

---

# 10. PDF/export stack

## Recommended package

* `WeasyPrint`

Why:

* works well from HTML templates
* easier to control layout than low-level PDF libraries
* can reuse your app styling

## Export types

* plan summary PDF
* printable HTML view
* optional CSV export later

## PDF contents

* app branding
* plan title
* debt list
* payoff strategy
* debt-free date
* total interest
* total paid
* monthly summary
* payoff order

---

# 11. Email setup

## Needed for

* email verification
* password reset
* optional reminders later

## Recommended approach

Use Django email backend with:

* console backend for dev
* SMTP or transactional provider for prod

## .env variables

* `EMAIL_HOST`
* `EMAIL_PORT`
* `EMAIL_HOST_USER`
* `EMAIL_HOST_PASSWORD`
* `EMAIL_USE_TLS`
* `DEFAULT_FROM_EMAIL`

---

# 12. Billing stack

You may not launch with billing on day one, but the app should be built so billing can be added cleanly.

## Recommended

* Stripe

## Initial monetization options

* free plan
* one-time paid unlock
* optional subscription later

## Suggested MVP billing triggers

Paid unlock enables:

* save multiple plans
* export PDF
* compare unlimited scenarios
* spouse/family sharing later

---

# 13. Logging and error handling

People forget this constantly.

## Logging requirements

Log:

* server errors
* login failures
* plan creation
* export generation
* billing webhook issues later

## Suggested logging setup

* console log in dev
* rotating file log in prod
* separate error log if possible

Suggested log files:

* `logs/app.log`
* `logs/error.log`

---

# 14. Security requirements

Since this is finance-adjacent, you want basic SaaS hygiene even if it is not pulling bank data.

## Required

* CSRF enabled
* secure cookies in production
* HTTPS only in production
* password hashing via Django defaults
* email verification
* do not store bank credentials
* do not ask for SSNs
* validation on all numeric fields
* admin not exposed casually
* `.env` secrets not committed
* debug off in production

## Legal pages needed

* privacy policy
* terms of service
* financial disclaimer

## Example disclaimer

“This tool provides educational payoff projections and does not constitute financial, legal, or tax advice.”

---

# 15. Environment and configuration

## Environment management

Use `.env` with `python-dotenv` or `django-environ`.

## Example `.env` values

```env
DEBUG=True
SECRET_KEY=replace-me
ALLOWED_HOSTS=127.0.0.1,localhost

DATABASE_URL=sqlite:///db.sqlite3

EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@example.com

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

STRIPE_SECRET_KEY=
STRIPE_PUBLIC_KEY=
STRIPE_WEBHOOK_SECRET=
```

---

# 16. Required packages

A good `requirements.txt` starter:

```txt
Django>=5.1,<6.0
django-allauth>=65.0.0
django-environ>=0.11.2
python-dotenv>=1.0.1
WeasyPrint>=62.3
whitenoise>=6.7.0
Pillow>=10.4.0
gunicorn>=23.0.0
waitress>=3.0.0
```

Optional dev tools:

```txt
black>=24.8.0
ruff>=0.6.9
pytest>=8.3.3
pytest-django>=4.9.0
```

If using HTMX/Alpine/Chart.js via CDN, no Python package needed.

---

# 17. run.bat requirements

You specifically mentioned wanting a Windows batch file that:

* creates venv if missing
* activates it
* installs dependencies
* runs migrations
* starts app

That is exactly right.

## `run.bat` responsibilities

* check for `.venv`
* create `.venv` if missing
* activate `.venv`
* upgrade pip
* install `requirements.txt`
* create migration files if needed
* run migrations
* optionally collect static
* start Django development server

## Example behavior outline

```bat
@echo off
setlocal

if not exist .venv (
    py -m venv .venv
)

call .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
    copy .env.example .env
)

python manage.py makemigrations
python manage.py migrate

python manage.py runserver
```

You may also want:

* optional superuser creation note
* optional `collectstatic` prompt in prod mode

---

# 18. run.sh requirements

Even if you are Windows-first, include this.

## `run.sh`

* create `.venv` if missing
* activate venv
* install dependencies
* create `.env` from example if missing
* migrate
* runserver

---

# 19. Developer workflow requirements

You’ve mentioned before you want structured startup rules. This project should absolutely have them.

## Recommended workflow rules

* always work inside `.venv`
* never run app without activated environment
* keep a natural-language changelog
* all dependencies in `requirements.txt`
* all secrets in `.env`
* migrations committed to Git
* no hardcoded secrets
* run app through `run.bat` or `run.sh`
* SQLite DB file excluded or handled appropriately per policy
* update changelog with every meaningful change

---

# 20. Suggested `.gitignore`

Very important.

```gitignore
.venv/
__pycache__/
*.pyc
.env
db.sqlite3
media/
staticfiles/
logs/
.pytest_cache/
.vscode/
.idea/
```

If you want sample DB files for demo, that is separate.

---

# 21. Recommended README contents

The README should include:

## Sections

* project overview
* stack
* setup instructions
* environment variables
* how to run locally
* how to create superuser
* how to run tests
* deployment notes
* feature overview
* known future enhancements

---

# 22. Recommended CHANGELOG format

Since you like a natural-language changelog, use something simple.

## Example

```md
# Changelog

## 2026-03-17
- Set up Django project structure with accounts, plans, calculator, exports, and legal apps.
- Added local venv startup scripts for Windows and Linux.
- Added email/password authentication and prepared Google SSO integration.
- Implemented initial debt entry models and payoff engine scaffolding.
```

---

# 23. Deployment recommendation

## MVP deployment options

* small Linux VPS
* Caddy or Nginx reverse proxy
* Gunicorn app server
* SQLite initially acceptable
* WhiteNoise for static if simple

## If deploying on Windows

Use:

* Waitress
* reverse proxy optional depending on environment

## Better production later

* PostgreSQL
* Redis
* Celery
* background tasks for reminders/exports

But that is later, not needed to launch.

---

# 24. Production settings checklist

People forget these too.

## In production

* `DEBUG=False`
* strong secret key
* allowed hosts configured
* secure cookies on
* CSRF trusted origins set
* static files collected
* error logging enabled
* HTTPS configured
* admin path not default if you want extra obscurity

---

# 25. Testing scope

At minimum, test:

## Unit tests

* payoff engine calculations
* snowball ordering
* avalanche ordering
* custom ordering
* zero-interest debt
* overpayment rollover
* exact final payoff month

## Integration tests

* login
* signup
* plan creation
* result generation
* PDF export

The payoff engine is the most important thing to test.

---

# 26. Things developers forget that should be included

Here’s the “all the crap I forgot” section.

## Must include

* custom user model decision at project start
* `.env.example`
* `run.bat`
* `run.sh`
* changelog
* privacy policy page
* terms page
* financial disclaimer
* form validation errors shown clearly
* empty states for first-time user
* print stylesheet
* mobile responsive layout
* admin list filters/search
* logging
* favicon / basic branding assets
* session timeout behavior
* password reset flow
* email verification flow
* 404 and 500 pages
* loading states for calculation/export
* success/error toast messages
* chart fallback if JS fails
* export page that works without weird formatting
* migration strategy
* backup plan for SQLite file in production
* analytics events

---

# 27. Recommended MVP scope lock

To protect the build:

## Build now

* Django app
* SQLite
* email/password auth
* Google SSO if easy, otherwise phase 1.1
* debt plans
* debt items
* payoff engine
* results dashboard
* comparison view
* PDF export
* print view
* changelog
* startup scripts
* admin panel
* legal pages

## Do not build yet

* bank integrations
* plaid
* advanced budgeting
* AI chat
* multi-user family collaboration
* SMS reminders
* billing complexity beyond simple Stripe setup
* mobile app
* API-first architecture

---

# 28. Suggested dev handoff summary

You can give your dev this:

> Build a Django web application called Debt Freedom Planner using Python 3.12, SQLite, Django templates, HTMX, Alpine.js, and Bootstrap 5.
> Authentication should support email/password and preferably Google SSO via django-allauth.
> The app should run locally through a `run.bat` script that creates and activates a `.venv`, installs dependencies, copies `.env.example` to `.env` if needed, runs migrations, and starts the server.
>
> The app must include:
>
> * user accounts
> * debt plan CRUD
> * debt item CRUD
> * payoff engine with snowball, avalanche, and custom order
> * summary dashboard
> * month-by-month payoff schedule
> * scenario comparison
> * PDF export and print view
> * Django admin
> * legal pages
> * logging
> * responsive templates
>
> Keep the architecture modular with separate Django apps for accounts, plans, calculator, exports, and legal.
> Do not include bank integrations or budgeting features in MVP.

---

# 29. My recommendation on one point

Between Google SSO and email/password:

## For your audience

Email/password is the real must-have.

Google SSO is nice, but your demographic may be just as comfortable with plain email signup, and it reduces friction in development if needed.

So I would say:

* **email/password required**
* **Google SSO optional but recommended**

---

# 30. Best practical setup for you

If I were locking this for your project, I’d choose:

* Django
* Python 3.12
* SQLite
* Django templates
* HTMX
* Alpine.js
* Bootstrap 5
* django-allauth
* WeasyPrint
* WhiteNoise
* `.venv`
* `requirements.txt`
* `.env`
* `run.bat`
* `run.sh`
* Git
* Black
* Ruff
* Django admin
* Stripe later

---

_____________________


---

# 🧩 Where the logo should go

## ✅ Correct location (Django standard)

Put your logo here:

```
static/img/logo.png
```

or if you want to be more organized:

```
static/img/branding/logo.png
```

---

# 📁 Recommended structure for assets

I’d suggest this (clean and scalable):

```
static/
├── css/
├── js/
├── img/
│   ├── branding/
│   │   ├── logo.png
│   │   ├── logo-dark.png
│   │   ├── logo-light.png
│   │   └── favicon.png
│   ├── icons/
│   └── illustrations/
└── vendor/
```

---

# 🧠 Why this matters

* `static/` = **assets that ship with your app**
* Logos are NOT user uploads → so they do NOT go in `/media/`
* Keeping branding separate avoids chaos later when you add:

  * dark mode
  * PDFs
  * emails
  * marketing pages

---

# 🖼️ How to use it in templates

In your Django template:

```html
{% load static %}

<img src="{% static 'img/branding/logo.png' %}" alt="Logo">
```

---

# 📄 What about the favicon?

Put it here:

```
static/img/branding/favicon.ico
```

Then in `base.html`:

```html
<link rel="icon" href="{% static 'img/branding/favicon.ico' %}">
```

---

# 📄 What about PDF exports?

Your PDF generator (WeasyPrint) will also use static paths:

```html
<img src="{{ STATIC_ROOT }}/img/branding/logo.png">
```

OR better (more reliable):

```html
<img src="{% static 'img/branding/logo.png' %}">
```

Make sure static files are properly configured for PDF rendering.

---

# 📧 What about emails?

Same static path applies, but:

* emails may need **absolute URLs**

Example:

```html
<img src="https://yourdomain.com/static/img/branding/logo.png">
```

---

# 🚨 Common mistakes (avoid these)

❌ Putting logo in `/media/`
→ that’s for user uploads only

❌ Putting logo inside an app folder like:

```
core/static/logo.png
```

→ works, but becomes messy across apps

❌ Hardcoding `/static/...` without `{% static %}`
→ breaks in production sometimes

---

# 🧠 My recommendation for YOUR project

Since you’re thinking long-term SaaS + branding:

👉 Use:

```
static/img/branding/logo.png
```

And also include:

```
logo-dark.png
logo-light.png
favicon.ico
```

Even if you don’t use them yet.

---

# 💡 Bonus (future-proofing)

If you plan to:

* generate PDFs
* send emails
* add marketing pages

You may also want:

```
static/img/branding/logo-horizontal.png
static/img/branding/logo-mark.png
```

---
