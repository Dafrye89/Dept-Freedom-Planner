# Changelog

## 2026-03-17
- Rebuilt the project as a full Django application with `core`, `accounts`, `plans`, `calculator`, `exports`, `legal`, and `billing` apps.
- Added a custom user model, founder bootstrap command, free-versus-paid access policy, and founder-only admin link behavior for `dafrye89`.
- Implemented the Python payoff engine with snowball, avalanche, custom ordering, schedule generation, comparisons, and stalled-plan handling.
- Built the guided elderly-friendly planner flow, saved plan dashboard, manual paid scenario lab, print view, and working PDF export fallback for Windows.
- Added Django tests for the payoff engine, access policy, auth flow, save limits, print/PDF export, and founder visibility rules.
- Replaced the old Vite browser smoke with a Django-aware Playwright QA flow that captures screenshots for anonymous, free, paid, founder, desktop, and mobile states.
- Replaced the old Node startup scripts with Django `run.bat` and `run.sh` workflows.
