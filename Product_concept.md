# Product concept

**Working title:** Debt Freedom Planner
**Core promise:** “See the fastest path to becoming debt-free.”

This is **not** a budgeting app, bank sync tool, or finance platform.
It is a **focused calculator + planner** that helps users:

* enter their debts
* choose a payoff strategy
* see payoff date
* see total interest paid
* get a month-by-month plan
* print or save their plan

That focus is what makes it buildable and marketable.

---

# 1. Product goals

## Primary goal

Give users a clear, motivating debt payoff plan in under 5 minutes.

## Business goal

Convert users through:

* free calculator
* optional saved account
* premium plan export / advanced scenarios / reminders

## Non-goals for MVP

Do **not** build:

* bank account integrations
* credit score monitoring
* budgeting system
* investment tools
* tax tools
* loan refinancing marketplace
* AI chatbot as core feature

---

# 2. Target user

## Primary user

Adults 35–65+, especially people who:

* have multiple debts
* want a simple plan
* dislike spreadsheets
* want clarity fast
* may follow debt-free or conservative finance content

## User mindset

They are asking:

* “Which debt should I pay first?”
* “How long will this take?”
* “How much interest am I wasting?”
* “What happens if I add $200 more per month?”

---

# 3. Core MVP features

## A. Debt entry

User can add multiple debts.

### Fields per debt

* Debt name

  * examples: Credit Card 1, Car Loan, Personal Loan
* Current balance
* Interest rate (APR %)
* Minimum monthly payment
* Optional due day
* Optional lender name
* Optional notes

### Validation

* balance > 0
* APR >= 0
* minimum payment > 0

---

## B. Monthly extra payment input

User enters:

* total extra amount they can pay each month beyond minimums

Example:

* minimums total = $730
* extra monthly payment = $300
* total monthly debt payment = $1,030

---

## C. Payoff strategies

User can choose one of:

### 1. Snowball

Pay smallest balance first.

### 2. Avalanche

Pay highest interest first.

### 3. Custom order

User drags debts into their preferred order.

---

## D. Results dashboard

Once debts are entered, show:

* estimated debt-free date
* months until debt-free
* total interest paid
* total amount paid
* first debt to attack
* next 12 months summary
* visual progress chart

---

## E. Payoff schedule

Detailed month-by-month table:

Columns:

* month number
* calendar month
* debt name
* starting balance
* interest charged
* payment made
* ending balance
* status

Must reflect rollover:
when one debt is paid off, that payment amount rolls into the next target debt.

---

## F. Scenario comparison

Let user compare:

* Snowball vs Avalanche
* current plan vs adding extra money

Show:

* difference in payoff date
* difference in total interest

---

## G. Export / print

User can:

* print payoff plan
* export PDF summary

PDF should include:

* user’s debt list
* chosen strategy
* payoff date
* total interest
* monthly summary
* motivational cover page

---

# 4. Nice-to-have features after MVP

Not required for first release, but strong next steps:

## Phase 2

* save progress with login
* reminder emails
* “what if” sliders for extra payment
* spouse/shared household view
* payoff milestone tracking
* visual debt thermometer
* payoff calendar
* mobile-first dashboard polish

## Phase 3

* document vault for statements
* RAG-based document lookup
* payoff recommendations from uploaded statements
* refinance suggestions
* emotional/motivational progress messaging

---

# 5. User flow

## Anonymous user flow

1. lands on homepage
2. clicks “Calculate My Debt Payoff”
3. enters debts
4. enters extra monthly payment
5. chooses strategy
6. sees results instantly
7. prompted to:

   * save plan
   * export PDF
   * create account

## Logged-in user flow

1. login
2. dashboard shows saved plans
3. user edits debts
4. recalculates plan
5. exports or prints updated plan

---

# 6. Screens needed

## 1. Landing page

Sections:

* headline
* subheadline
* CTA button
* simple explanation
* benefits
* comparison example
* FAQ

### Suggested headline

**Get a clear plan to become debt-free.**

### CTA

**See My Payoff Plan**

---

## 2. Debt entry screen

Card/table UI where user can:

* add debt
* edit debt
* delete debt

At bottom:

* total debt balance
* total minimum payments

---

## 3. Strategy screen

Radio cards:

* Snowball
* Avalanche
* Custom

With brief explanation under each.

---

## 4. Results dashboard

Top summary cards:

* debt-free in X months
* payoff date
* total interest
* total paid

Then:

* payoff order
* chart
* schedule preview
* CTA to export/save

---

## 5. Full schedule screen

Paginated or collapsible month-by-month schedule.

---

## 6. Account/login pages

Simple email/password or Google login.

---

# 7. Suggested UI style

This audience needs:

* clean
* calm
* trustworthy
* not flashy
* not “crypto fintech”

## Design direction

* white background
* dark text
* muted blues / greens
* large readable font
* obvious buttons
* simple cards
* minimal jargon

## Tone

Use:

* “Debt-free date”
* “Monthly plan”
* “Interest paid”

Avoid:

* “financial optimization engine”
* “AI-powered debt intelligence”
* overly technical terms

---

# 8. Calculation logic

## Inputs

For each debt:

* balance
* APR
* minimum payment

Global:

* extra monthly payment
* chosen strategy

## Monthly calculation behavior

Each month:

1. calculate monthly interest for each unpaid debt
2. apply minimum payments to all debts
3. apply extra payment to current target debt
4. if target debt is paid off, rollover remaining amount to next debt in same month if possible
5. continue until all balances reach zero

## Monthly interest formula

Use:
monthly interest = current balance * (APR / 100 / 12)

## Strategy sorting

### Snowball

Sort by:

1. lowest balance
2. then highest APR as tie-breaker

### Avalanche

Sort by:

1. highest APR
2. then lowest balance as tie-breaker

### Custom

Use user-defined order

## Edge cases

* payment exceeds remaining balance
* zero-interest debt
* minimum payment lower than accrued monthly interest
* single debt only
* no extra monthly payment
* invalid inputs

---

# 9. Tech recommendation

Since you lean Python and web, this is a very reasonable stack:

## Backend

* Python
* Flask or Django

For speed and auth/admin, Django is strong.
For a lighter build, Flask works.

## Frontend

* server-rendered templates initially, or
* lightweight JS frontend

Good options:

* Django templates + HTMX
* Flask + Jinja + Alpine.js
* React only if the dev strongly prefers it

## Database

* PostgreSQL in production
* SQLite for local dev

## Auth

* email/password
* optional Google login later

## PDF

* WeasyPrint or ReportLab
* or HTML-to-PDF approach

## Charts

* Chart.js

---

# 10. Suggested data model

## User

* id
* email
* password hash
* created_at

## DebtPlan

* id
* user_id nullable for guest temp save
* name
* strategy_type
* extra_monthly_payment
* total_balance
* projected_payoff_date
* total_interest
* total_paid
* created_at
* updated_at

## DebtItem

* id
* debt_plan_id
* name
* lender_name nullable
* balance
* apr
* minimum_payment
* due_day nullable
* notes nullable
* payoff_order nullable

## PayoffSnapshot or PayoffScheduleRow

Optional to persist if needed:

* id
* debt_plan_id
* month_index
* calendar_month
* debt_item_id
* starting_balance
* interest
* payment
* ending_balance

Could also generate schedule dynamically instead of storing every row.

---

# 11. Pricing model

## Best MVP pricing

### Free

* calculate plan
* compare Snowball vs Avalanche
* limited on-screen schedule

### Paid: $9–$19/month or $29–$49 one-time

* save plans
* export PDF
* unlimited scenarios
* reminders
* household sharing later

Honestly, for this kind of tool, a **one-time purchase option** may convert better with your audience than subscription only.

Example:

* Free plan
* $29 one-time “Lifetime Planner”
* or $8/month

---

# 12. Conversion hooks

These should be built into the UX.

## On results page

Show:

* “You could be debt-free by June 2029.”
* “You could save $8,412 in interest with Avalanche.”
* “Add $150/month and get out of debt 14 months sooner.”

That emotional clarity is the product.

---

# 13. Admin needs

Admin should be able to:

* see users
* see saved plans
* see subscription/payment status
* see most common debt totals / strategy usage
* manage feature flags or pricing text

If using Django, admin is basically free.

---

# 14. Metrics to track

Track:

* landing page visits
* calculator starts
* calculator completions
* account creations
* PDF exports
* paid conversions
* strategy chosen
* average number of debts entered
* average extra monthly payment

---

# 15. Security and privacy

Because it is finance-adjacent:

* use HTTPS only
* encrypt passwords properly
* avoid asking for bank credentials
* minimize personally sensitive data
* make privacy policy clear
* allow plan deletion

For MVP, do not store SSNs, bank logins, or full account numbers.

---

# 16. MVP build order

## Sprint 1

* landing page
* debt entry UI
* payoff calculation engine
* strategy selection
* results summary

## Sprint 2

* charts
* full payoff schedule
* PDF export
* guest session save

## Sprint 3

* account creation/login
* saved plans
* billing integration
* analytics

---

# 17. Dev handoff summary

## Build this:

A web app where users can enter multiple debts, choose Snowball/Avalanche/custom payoff order, add extra monthly payment, and instantly see:

* debt-free date
* total interest
* monthly schedule
* payoff comparison
* printable/exportable plan

## Do not build yet:

* bank sync
* budgeting
* credit reports
* investment tools
* complex AI assistant

---

# 18. Suggested feature copy for developer/designer

## Homepage copy

**Headline:**
Get a clear plan to pay off your debt.

**Subheadline:**
Add your debts, choose a payoff strategy, and see exactly when you could become debt-free.

**Primary CTA:**
See My Plan

## Results page copy

**Debt-free by:**
[Date]

**Total interest:**
[$]

**Best next step:**
Focus on [Debt Name] first.

---

# 19. Recommendation for your actual launch

For your audience, I’d position it as:

**“Debt Freedom Planner”**
not
“AI Financial Optimization Platform”

And I would market it with:

* debt-free date hooks
* interest savings hooks
* “simple plan in 5 minutes” hooks

---