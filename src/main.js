import "./styles.css";
import {
  createChartPath,
  createComparisons,
  reorderCustomDebts,
  solvePayoffPlan
} from "./payoff-engine.js";

const STORAGE_KEY = "debt-freedom-planner-state";

const starterDebts = [
  {
    id: "credit-card-a",
    name: "Freedom Card",
    lender: "Liberty Bank",
    balance: 2480,
    apr: 24.99,
    minimumPayment: 95,
    dueDay: "12",
    notes: "Used for groceries and emergency repairs.",
    customRank: 1
  },
  {
    id: "store-card",
    name: "General Store Card",
    lender: "General Market",
    balance: 3100,
    apr: 19.5,
    minimumPayment: 90,
    dueDay: "18",
    notes: "Seasonal purchases and household items.",
    customRank: 2
  },
  {
    id: "car-loan",
    name: "Truck Loan",
    lender: "Roadway Credit",
    balance: 11700,
    apr: 7.2,
    minimumPayment: 315,
    dueDay: "4",
    notes: "Family vehicle.",
    customRank: 3
  },
  {
    id: "personal-loan",
    name: "Home Repair Loan",
    lender: "Homefront Lending",
    balance: 16900,
    apr: 10.9,
    minimumPayment: 420,
    dueDay: "25",
    notes: "Roof and storm damage repairs.",
    customRank: 4
  }
];

const initialState = {
  planName: "Debt Freedom Roadmap",
  householdName: "The Freedom Household",
  extraPayment: 350,
  strategy: "snowball",
  debts: starterDebts,
  form: emptyDebtForm(),
  scheduleLimit: 18,
  onboarding: "Designed to turn complicated debt math into one clear American-style payoff road map."
};

function emptyDebtForm() {
  return {
    id: "",
    name: "",
    lender: "",
    balance: "",
    apr: "",
    minimumPayment: "",
    dueDay: "",
    notes: ""
  };
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(Number(value) || 0);
}

function formatMoney(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(Number(value) || 0);
}

function formatPercent(value) {
  return `${Number(value || 0).toFixed(2)}%`;
}

function saveState(state) {
  const serializable = {
    planName: state.planName,
    householdName: state.householdName,
    extraPayment: state.extraPayment,
    strategy: state.strategy,
    debts: state.debts,
    scheduleLimit: state.scheduleLimit,
    onboarding: state.onboarding
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(serializable));
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return structuredClone(initialState);
    }

    const parsed = JSON.parse(raw);
    return {
      ...structuredClone(initialState),
      ...parsed,
      debts: Array.isArray(parsed.debts) && parsed.debts.length ? parsed.debts : starterDebts,
      form: emptyDebtForm()
    };
  } catch (error) {
    return structuredClone(initialState);
  }
}

const state = loadState();
const root = document.querySelector("#app");

function getPlanOutput() {
  return solvePayoffPlan({
    debts: state.debts,
    extraPayment: state.extraPayment,
    strategy: state.strategy,
    title: state.planName
  });
}

function getComparisonOutput() {
  return createComparisons({
    debts: state.debts,
    extraPayment: state.extraPayment,
    title: state.planName
  });
}

function getBaselineOutput() {
  return solvePayoffPlan({
    debts: state.debts,
    extraPayment: 0,
    strategy: state.strategy,
    title: state.planName
  });
}

function render() {
  saveState(state);

  const plan = getPlanOutput();
  const comparisons = getComparisonOutput();
  const baseline = getBaselineOutput();
  const chartPath = createChartPath(plan.monthlyTotals);
  const debtCount = state.debts.length;
  const interestSaved = Math.max(0, baseline.summary.totalInterest - plan.summary.totalInterest);
  const acceleratedMonthsSaved = Math.max(
    0,
    plan.summary.monthsToPayoff - comparisons.accelerated.summary.monthsToPayoff
  );
  const firstFocus = plan.summary.firstTarget || "your first debt";
  const firstDebtWin = plan.summary.fastestWinMonths
    ? `${plan.summary.fastestWinMonths} month${plan.summary.fastestWinMonths === 1 ? "" : "s"}`
    : "no time";
  const scheduleRows = plan.schedule.slice(0, state.scheduleLimit);
  const alternativeSummary = state.strategy === "snowball" ? comparisons.avalanche : comparisons.snowball;
  const alternativeDiff = Math.max(0, plan.summary.totalInterest - alternativeSummary.summary.totalInterest);
  const customOrderDebts = [...state.debts].sort(
    (left, right) => (left.customRank || 0) - (right.customRank || 0)
  );

  root.innerHTML = `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="sidebar__backdrop"></div>
        <div class="brand-card">
          <img class="brand-card__logo" src="/logo.png" alt="Debt Freedom Planner logo" />
          <div>
            <span class="eyebrow">Debt Freedom Planner</span>
            <h1>${escapeHtml(state.planName)}</h1>
            <p>${escapeHtml(state.onboarding)}</p>
          </div>
        </div>

        <nav class="sidebar__nav" aria-label="Primary">
          <a href="#command-center" class="nav-link nav-link--active">Command center</a>
          <a href="#debts" class="nav-link">Debt roster</a>
          <a href="#comparison" class="nav-link">Strategy lab</a>
          <a href="#schedule" class="nav-link">Payoff schedule</a>
          <a href="#print" class="nav-link">Print and export</a>
        </nav>

        <div class="trust-card">
          <span class="eyebrow">Mission</span>
          <h2>One road out of debt.</h2>
          <p>
            The planner keeps the tone patriotic and steady: bold red, white, and blue accents,
            plain language, and no gimmicks.
          </p>
          <ul class="trust-list">
            <li>Local data saved in your browser</li>
            <li>Snowball, avalanche, and custom order</li>
            <li>Printable family-ready plan</li>
          </ul>
        </div>
      </aside>

      <main class="main-shell">
        <section class="hero">
          <div class="hero__copy">
            <span class="eyebrow eyebrow--light">American road map to debt freedom</span>
            <h2>You could be debt-free by <span>${plan.summary.projectedPayoffDateLabel}</span>.</h2>
            <p>
              ${escapeHtml(state.householdName)} is carrying ${formatCurrency(plan.summary.totalDebt)} across
              ${debtCount} debt${debtCount === 1 ? "" : "s"}. With ${formatCurrency(
                plan.summary.extraPayment
              )} in extra monthly firepower, the current ${plan.strategyLabel.toLowerCase()} plan
              pays it off in ${plan.summary.monthsToPayoff} months.
            </p>
            <div class="hero__actions">
              <button type="button" data-action="print" class="button button--ghost">Print plan</button>
              <button type="button" data-action="export" class="button button--light">Export PDF</button>
            </div>
          </div>

          <div class="hero__stats">
            ${statCard("Total debt", formatCurrency(plan.summary.totalDebt), "Loaded from your current balances")}
            ${statCard("Interest ahead", formatCurrency(plan.summary.totalInterest), "Projected with this strategy")}
            ${statCard("Monthly payment", formatCurrency(plan.summary.monthlyPayment), "Minimums plus extra")}
            ${statCard("Fastest victory", firstDebtWin, `${escapeHtml(firstFocus)} is the first target`)}
          </div>
        </section>

        <section id="command-center" class="dashboard-grid">
          <article class="panel panel--form">
            <div class="panel__header">
              <div>
                <span class="eyebrow">Command center</span>
                <h3>Update the plan</h3>
              </div>
              <span class="badge badge--accent">${plan.strategyLabel} active</span>
            </div>

            <div class="control-grid">
              <label class="field">
                <span>Plan name</span>
                <input data-field="planName" type="text" value="${escapeAttribute(state.planName)}" />
              </label>
              <label class="field">
                <span>Household label</span>
                <input data-field="householdName" type="text" value="${escapeAttribute(state.householdName)}" />
              </label>
              <label class="field field--wide">
                <span>Extra monthly payment</span>
                <input data-field="extraPayment" type="number" min="0" step="25" value="${escapeAttribute(
                  state.extraPayment
                )}" />
              </label>
            </div>

            <div class="strategy-toggle" role="group" aria-label="Choose payoff strategy">
              ${strategyButton("snowball", "Snowball", "Small balances first for early wins.")}
              ${strategyButton("avalanche", "Avalanche", "Highest APR first to save interest.")}
              ${strategyButton("custom", "Custom order", "Move debts up or down and pay them your way.")}
            </div>

            <div class="panel-callout">
              <strong>Interest saved:</strong>
              <span>${formatCurrency(interestSaved)} compared with making only minimum payments.</span>
            </div>
          </article>

          <article class="panel panel--insight">
            <div class="panel__header">
              <div>
                <span class="eyebrow">At a glance</span>
                <h3>What changes the outcome</h3>
              </div>
              <span class="badge">${formatCurrency(plan.summary.extraPayment)} extra</span>
            </div>

            <div class="metric-grid">
              ${metricCard("Debt-free date", plan.summary.projectedPayoffDateLabel, "Steady target based on current entries")}
              ${metricCard("Total paid", formatCurrency(plan.summary.totalPaid), "Principal plus projected interest")}
              ${metricCard("Interest saved", formatCurrency(interestSaved), "Against minimum-payment baseline")}
              ${metricCard("Accelerated option", `${acceleratedMonthsSaved} months faster`, "If you add another $150")}
            </div>

            <div class="priority-card">
              <span class="eyebrow">Next step</span>
              <h4>Attack ${escapeHtml(firstFocus)} first.</h4>
              <p>
                Pay every extra dollar there until the balance hits zero. The full payment then rolls into the next
                debt automatically.
              </p>
            </div>
          </article>
        </section>

        <section id="debts" class="dashboard-grid dashboard-grid--asymmetric">
          <article class="panel">
            <div class="panel__header">
              <div>
                <span class="eyebrow">Debt roster</span>
                <h3>Every account in one place</h3>
              </div>
              <span class="badge">${debtCount} active debt${debtCount === 1 ? "" : "s"}</span>
            </div>

            <div class="table-wrap">
              <table class="debt-table">
                <thead>
                  <tr>
                    <th>Debt</th>
                    <th>Balance</th>
                    <th>APR</th>
                    <th>Minimum</th>
                    <th>Due</th>
                    <th>Progress</th>
                    <th>Order</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${customOrderDebts
                    .map((debt) => {
                      const resultDebt = plan.debts.find((item) => item.id === debt.id) || debt;
                      return `
                        <tr>
                          <td>
                            <strong>${escapeHtml(debt.name)}</strong>
                            <span>${escapeHtml(debt.lender || "No lender listed")}</span>
                          </td>
                          <td>${formatCurrency(debt.balance)}</td>
                          <td>${formatPercent(debt.apr)}</td>
                          <td>${formatCurrency(debt.minimumPayment)}</td>
                          <td>${escapeHtml(debt.dueDay || "N/A")}</td>
                          <td>
                            <div class="progress-chip">
                              <div class="progress-chip__bar">
                                <span style="width:${Math.max(5, Number(resultDebt.progress || 0))}%"></span>
                              </div>
                              <small>${Math.round(Number(resultDebt.progress || 0))}% paid down</small>
                            </div>
                          </td>
                          <td>
                            <div class="order-controls">
                              <span class="badge badge--small">#${debt.customRank || 1}</span>
                              <button type="button" class="icon-button" data-action="move-up" data-id="${debt.id}" ${
                                state.strategy !== "custom" ? "disabled" : ""
                              }>↑</button>
                              <button type="button" class="icon-button" data-action="move-down" data-id="${debt.id}" ${
                                state.strategy !== "custom" ? "disabled" : ""
                              }>↓</button>
                            </div>
                          </td>
                          <td>
                            <div class="row-actions">
                              <button type="button" class="button button--tiny" data-action="edit-debt" data-id="${debt.id}">Edit</button>
                              <button type="button" class="button button--tiny button--danger" data-action="delete-debt" data-id="${debt.id}">Delete</button>
                            </div>
                          </td>
                        </tr>
                      `;
                    })
                    .join("")}
                </tbody>
              </table>
            </div>
          </article>

          <article class="panel panel--form">
            <div class="panel__header">
              <div>
                <span class="eyebrow">Debt editor</span>
                <h3>${state.form.id ? "Edit debt" : "Add a debt"}</h3>
              </div>
              <span class="badge badge--accent">${state.form.id ? "Update row" : "New account"}</span>
            </div>

            <form id="debt-form" class="debt-form">
              <div class="control-grid">
                <label class="field">
                  <span>Debt name</span>
                  <input name="name" required value="${escapeAttribute(state.form.name)}" />
                </label>
                <label class="field">
                  <span>Lender</span>
                  <input name="lender" value="${escapeAttribute(state.form.lender)}" />
                </label>
                <label class="field">
                  <span>Balance</span>
                  <input name="balance" type="number" min="0.01" step="0.01" required value="${escapeAttribute(
                    state.form.balance
                  )}" />
                </label>
                <label class="field">
                  <span>APR</span>
                  <input name="apr" type="number" min="0" step="0.01" required value="${escapeAttribute(state.form.apr)}" />
                </label>
                <label class="field">
                  <span>Minimum payment</span>
                  <input name="minimumPayment" type="number" min="0.01" step="0.01" required value="${escapeAttribute(
                    state.form.minimumPayment
                  )}" />
                </label>
                <label class="field">
                  <span>Due day</span>
                  <input name="dueDay" type="number" min="1" max="31" value="${escapeAttribute(state.form.dueDay)}" />
                </label>
                <label class="field field--wide">
                  <span>Notes</span>
                  <textarea name="notes" rows="3">${escapeHtml(state.form.notes)}</textarea>
                </label>
              </div>

              <div class="form-actions">
                <button type="submit" class="button button--primary">${state.form.id ? "Save changes" : "Add debt"}</button>
                <button type="button" class="button button--ghost" data-action="reset-form">Clear</button>
              </div>
            </form>
          </article>
        </section>

        <section id="comparison" class="dashboard-grid">
          <article class="panel">
            <div class="panel__header">
              <div>
                <span class="eyebrow">Strategy lab</span>
                <h3>Compare the payoff paths</h3>
              </div>
              <span class="badge">${formatCurrency(plan.summary.extraPayment)} monthly extra</span>
            </div>

            <div class="comparison-grid">
              ${comparisonCard(comparisons.snowball, state.strategy, "Best for momentum")}
              ${comparisonCard(comparisons.avalanche, state.strategy, "Best for interest savings")}
              ${comparisonCard(comparisons.custom, state.strategy, "Built from your custom order")}
            </div>

            <div class="comparison-callout">
              <strong>Alternative strategy delta:</strong>
              ${
                alternativeDiff
                  ? `${alternativeSummary.strategyLabel} saves ${formatCurrency(alternativeDiff)} compared with your current choice.`
                  : `${plan.strategyLabel} is already the strongest match for the way these debts are entered.`
              }
            </div>
          </article>

          <article class="panel">
            <div class="panel__header">
              <div>
                <span class="eyebrow">Balance glide path</span>
                <h3>Watch the debt fall away</h3>
              </div>
              <span class="badge badge--accent">${plan.summary.monthsToPayoff} months</span>
            </div>

            <div class="chart-card">
              <svg viewBox="0 0 560 170" role="img" aria-label="Total debt over time">
                <defs>
                  <linearGradient id="payoffLine" x1="0%" x2="100%">
                    <stop offset="0%" stop-color="#1b2b6b"></stop>
                    <stop offset="60%" stop-color="#376dff"></stop>
                    <stop offset="100%" stop-color="#c51f2f"></stop>
                  </linearGradient>
                </defs>
                <path class="chart-grid" d="M 0 154 H 560"></path>
                <path class="chart-grid" d="M 0 110 H 560"></path>
                <path class="chart-grid" d="M 0 66 H 560"></path>
                <path class="chart-line" d="${chartPath}"></path>
              </svg>

              <div class="chart-legend">
                <span>Start: ${formatCurrency(plan.summary.totalDebt)}</span>
                <span>Finish: ${plan.summary.projectedPayoffDateLabel}</span>
              </div>
            </div>

            <div class="timeline-card">
              <span class="eyebrow">12-month outlook</span>
              <div class="timeline-list">
                ${plan.monthlyTotals
                  .slice(0, 12)
                  .map(
                    (month) => `
                      <div class="timeline-row">
                        <strong>${month.monthLabel}</strong>
                        <span>${formatCurrency(month.totalEndingBalance)} remaining</span>
                        <small>${formatCurrency(month.payment)} paid</small>
                      </div>
                    `
                  )
                  .join("")}
              </div>
            </div>
          </article>
        </section>

        <section id="schedule" class="dashboard-grid dashboard-grid--stacked">
          <article class="panel">
            <div class="panel__header">
              <div>
                <span class="eyebrow">Monthly schedule</span>
                <h3>Every payment, every month</h3>
              </div>
              <div class="header-actions">
                <label class="field field--inline">
                  <span>Rows</span>
                  <select data-field="scheduleLimit">
                    ${[12, 18, 24, 36, plan.schedule.length]
                      .filter((value, index, values) => values.indexOf(value) === index)
                      .map(
                        (value) =>
                          `<option value="${value}" ${Number(state.scheduleLimit) === Number(value) ? "selected" : ""}>${
                            value === plan.schedule.length ? "All" : value
                          }</option>`
                      )
                      .join("")}
                  </select>
                </label>
              </div>
            </div>

            <div class="table-wrap">
              <table class="schedule-table">
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Debt</th>
                    <th>Starting</th>
                    <th>Interest</th>
                    <th>Payment</th>
                    <th>Ending</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${scheduleRows
                    .map(
                      (row) => `
                        <tr>
                          <td>${row.monthLabel}</td>
                          <td>${escapeHtml(row.debtName)}</td>
                          <td>${formatMoney(row.startingBalance)}</td>
                          <td>${formatMoney(row.interest)}</td>
                          <td>${formatMoney(row.payment)}</td>
                          <td>${formatMoney(row.endingBalance)}</td>
                          <td><span class="badge badge--small ${row.status === "Paid off" ? "badge--success" : ""}">${row.status}</span></td>
                        </tr>
                      `
                    )
                    .join("")}
                </tbody>
              </table>
            </div>
          </article>
        </section>

        <section id="print" class="dashboard-grid">
          <article class="panel">
            <div class="panel__header">
              <div>
                <span class="eyebrow">Print and export</span>
                <h3>Family-ready summary</h3>
              </div>
              <span class="badge">Browser PDF export supported</span>
            </div>

            <div class="print-sheet">
              <div class="print-sheet__brand">
                <img src="/logo.png" alt="Debt Freedom Planner logo" />
                <div>
                  <strong>${escapeHtml(state.planName)}</strong>
                  <span>${escapeHtml(state.householdName)}</span>
                </div>
              </div>
              <div class="print-sheet__stats">
                <div><span>Debt-free date</span><strong>${plan.summary.projectedPayoffDateLabel}</strong></div>
                <div><span>Total interest</span><strong>${formatCurrency(plan.summary.totalInterest)}</strong></div>
                <div><span>Total monthly payment</span><strong>${formatCurrency(plan.summary.monthlyPayment)}</strong></div>
              </div>
              <p>
                First focus: <strong>${escapeHtml(firstFocus)}</strong>. Stay consistent, roll every freed-up payment
                into the next debt, and review the plan monthly.
              </p>
              <div class="hero__actions">
                <button type="button" data-action="print" class="button button--primary">Open print dialog</button>
                <button type="button" data-action="export" class="button button--ghost">Save as PDF</button>
              </div>
            </div>
          </article>

          <article class="panel">
            <div class="panel__header">
              <div>
                <span class="eyebrow">Plain-language promise</span>
                <h3>Trustworthy by design</h3>
              </div>
              <span class="badge badge--accent">No bank sync</span>
            </div>

            <div class="copy-stack">
              <p>
                Debt Freedom Planner is a focused calculator and planner. It does not connect to bank accounts or pull
                credit data. It helps you decide what to pay first and when you could finally be debt-free.
              </p>
              <p>
                Financial disclaimer: these projections are educational estimates, not legal, tax, or financial advice.
                Review your real statements before making changes.
              </p>
            </div>
          </article>
        </section>
      </main>
    </div>
  `;

  bindHandlers();
}

function bindHandlers() {
  document.querySelector("#debt-form")?.addEventListener("submit", handleDebtSubmit);

  root.querySelectorAll("[data-field='planName'], [data-field='householdName'], [data-field='extraPayment']").forEach(
    (input) => {
      input.addEventListener("input", handleTopFieldChange);
    }
  );

  root.querySelector("[data-field='scheduleLimit']")?.addEventListener("change", (event) => {
    state.scheduleLimit = Number(event.target.value) || 18;
    render();
  });

  root.querySelectorAll("[data-strategy]").forEach((button) => {
    button.addEventListener("click", () => {
      state.strategy = button.dataset.strategy;
      render();
    });
  });

  root.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", handleAction);
  });
}

function handleTopFieldChange(event) {
  const { field } = event.target.dataset;
  if (field === "extraPayment") {
    state.extraPayment = Math.max(0, Number(event.target.value) || 0);
  } else {
    state[field] = event.target.value;
  }
  render();
}

function handleAction(event) {
  const action = event.currentTarget.dataset.action;
  const id = event.currentTarget.dataset.id;

  if (action === "print" || action === "export") {
    window.print();
    return;
  }

  if (action === "reset-form") {
    state.form = emptyDebtForm();
    render();
    return;
  }

  if (action === "delete-debt" && id) {
    state.debts = state.debts.filter((debt) => debt.id !== id).map((debt, index) => ({
      ...debt,
      customRank: index + 1
    }));
    state.form = emptyDebtForm();
    render();
    return;
  }

  if (action === "edit-debt" && id) {
    const debt = state.debts.find((item) => item.id === id);
    if (!debt) {
      return;
    }

    state.form = {
      id: debt.id,
      name: debt.name,
      lender: debt.lender || "",
      balance: debt.balance,
      apr: debt.apr,
      minimumPayment: debt.minimumPayment,
      dueDay: debt.dueDay || "",
      notes: debt.notes || ""
    };
    render();
    return;
  }

  if ((action === "move-up" || action === "move-down") && id) {
    state.debts = reorderCustomDebts(state.debts, id, action === "move-up" ? "up" : "down");
    render();
  }
}

function handleDebtSubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const payload = {
    id: state.form.id || createId(formData.get("name")),
    name: String(formData.get("name") || "").trim(),
    lender: String(formData.get("lender") || "").trim(),
    balance: Number(formData.get("balance") || 0),
    apr: Number(formData.get("apr") || 0),
    minimumPayment: Number(formData.get("minimumPayment") || 0),
    dueDay: String(formData.get("dueDay") || "").trim(),
    notes: String(formData.get("notes") || "").trim()
  };

  if (!payload.name || payload.balance <= 0 || payload.minimumPayment <= 0 || payload.apr < 0) {
    window.alert("Enter a debt name, a positive balance, a positive minimum payment, and a non-negative APR.");
    return;
  }

  if (state.form.id) {
    state.debts = state.debts.map((debt) => (debt.id === state.form.id ? { ...debt, ...payload } : debt));
  } else {
    state.debts = [
      ...state.debts,
      {
        ...payload,
        customRank: state.debts.length + 1
      }
    ];
  }

  state.form = emptyDebtForm();
  render();
}

function createId(label) {
  const base = String(label || "debt")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
  return `${base || "debt"}-${Date.now()}`;
}

function strategyButton(value, label, description) {
  const isActive = state.strategy === value;
  return `
    <button type="button" class="strategy-pill ${isActive ? "strategy-pill--active" : ""}" data-strategy="${value}">
      <strong>${label}</strong>
      <span>${description}</span>
    </button>
  `;
}

function statCard(label, value, detail) {
  return `
    <div class="hero-stat">
      <span>${label}</span>
      <strong>${value}</strong>
      <small>${detail}</small>
    </div>
  `;
}

function metricCard(label, value, detail) {
  return `
    <div class="metric-card">
      <span>${label}</span>
      <strong>${value}</strong>
      <small>${detail}</small>
    </div>
  `;
}

function comparisonCard(plan, activeStrategy, detail) {
  const isActive = plan.strategy === activeStrategy;
  return `
    <article class="comparison-card ${isActive ? "comparison-card--active" : ""}">
      <span class="eyebrow">${plan.strategyLabel}</span>
      <h4>${plan.summary.projectedPayoffDateLabel}</h4>
      <p>${detail}</p>
      <div class="comparison-card__stats">
        <strong>${plan.summary.monthsToPayoff} months</strong>
        <span>${formatCurrency(plan.summary.totalInterest)} interest</span>
      </div>
      <button type="button" class="button button--tiny ${isActive ? "button--ghost" : "button--primary"}" data-strategy="${
        plan.strategy
      }">${isActive ? "Current plan" : "Use this plan"}</button>
    </article>
  `;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}

render();
