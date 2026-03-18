const MAX_MONTHS = 600;
const EPSILON = 0.005;

function roundCurrency(value) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function clampPositive(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function monthLabel(date) {
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

function addMonths(baseDate, monthsToAdd) {
  return new Date(baseDate.getFullYear(), baseDate.getMonth() + monthsToAdd, 1);
}

function normalizeDebt(debt, index) {
  return {
    id: debt.id ?? `debt-${index + 1}`,
    name: debt.name?.trim() || `Debt ${index + 1}`,
    lender: debt.lender?.trim() || "",
    balance: roundCurrency(clampPositive(debt.balance)),
    apr: roundCurrency(Math.max(0, Number(debt.apr) || 0)),
    minimumPayment: roundCurrency(clampPositive(debt.minimumPayment)),
    dueDay: debt.dueDay ? String(debt.dueDay) : "",
    notes: debt.notes?.trim() || "",
    customRank: Number.isFinite(Number(debt.customRank)) ? Number(debt.customRank) : index + 1
  };
}

function sortDebts(activeDebts, strategy) {
  const debts = [...activeDebts];
  if (strategy === "avalanche") {
    debts.sort((left, right) => {
      if (right.apr !== left.apr) {
        return right.apr - left.apr;
      }
      if (left.balance !== right.balance) {
        return left.balance - right.balance;
      }
      return left.name.localeCompare(right.name);
    });
    return debts;
  }

  if (strategy === "custom") {
    debts.sort((left, right) => {
      if (left.customRank !== right.customRank) {
        return left.customRank - right.customRank;
      }
      return left.name.localeCompare(right.name);
    });
    return debts;
  }

  debts.sort((left, right) => {
    if (left.balance !== right.balance) {
      return left.balance - right.balance;
    }
    if (right.apr !== left.apr) {
      return right.apr - left.apr;
    }
    return left.name.localeCompare(right.name);
  });
  return debts;
}

export function createStrategyLabel(strategy) {
  if (strategy === "avalanche") {
    return "Avalanche";
  }
  if (strategy === "custom") {
    return "Custom";
  }
  return "Snowball";
}

export function solvePayoffPlan({
  debts,
  extraPayment = 0,
  strategy = "snowball",
  startDate = new Date(),
  title = "Debt Freedom Plan"
}) {
  const normalizedDebts = debts.map(normalizeDebt).filter((debt) => debt.balance > 0 && debt.minimumPayment > 0);
  const normalizedExtra = roundCurrency(Math.max(0, Number(extraPayment) || 0));
  const simulationStart = new Date(startDate.getFullYear(), startDate.getMonth(), 1);

  if (normalizedDebts.length === 0) {
    return {
      title,
      strategy,
      strategyLabel: createStrategyLabel(strategy),
      summary: {
        totalDebt: 0,
        monthsToPayoff: 0,
        totalInterest: 0,
        totalPaid: 0,
        totalMinimums: 0,
        extraPayment: normalizedExtra,
        monthlyPayment: normalizedExtra,
        projectedPayoffDateLabel: monthLabel(simulationStart),
        projectedPayoffDate: simulationStart,
        payoffOrder: [],
        firstTarget: null,
        fastestWinMonths: 0
      },
      debts: [],
      monthlyTotals: [],
      schedule: [],
      status: "empty"
    };
  }

  const debtState = normalizedDebts.map((debt) => ({
    ...debt,
    currentBalance: debt.balance,
    paidOffMonth: null,
    totalInterest: 0,
    totalPaid: 0
  }));

  const baseOrder = sortDebts(debtState, strategy);
  const schedule = [];
  const payoffOrder = [];
  const monthlyTotals = [];
  let totalInterest = 0;
  let totalPaid = 0;
  let stalledMonths = 0;

  for (let monthIndex = 0; monthIndex < MAX_MONTHS; monthIndex += 1) {
    const activeDebts = debtState.filter((debt) => debt.currentBalance > EPSILON);
    if (activeDebts.length === 0) {
      break;
    }

    const currentOrder = sortDebts(activeDebts, strategy);
    const monthDate = addMonths(simulationStart, monthIndex);
    const monthRows = [];
    let extraRemaining = normalizedExtra;
    let monthInterest = 0;
    let monthPaid = 0;
    const totalStartingBalance = roundCurrency(
      debtState.reduce((sum, debt) => sum + (debt.currentBalance > EPSILON ? debt.currentBalance : 0), 0)
    );

    for (const debt of currentOrder) {
      const startingBalance = roundCurrency(debt.currentBalance);
      const interest = roundCurrency(startingBalance * (debt.apr / 100 / 12));
      const balanceAfterInterest = roundCurrency(startingBalance + interest);
      const minimumPayment = roundCurrency(Math.min(balanceAfterInterest, debt.minimumPayment));
      debt.currentBalance = roundCurrency(balanceAfterInterest - minimumPayment);
      debt.totalInterest = roundCurrency(debt.totalInterest + interest);
      debt.totalPaid = roundCurrency(debt.totalPaid + minimumPayment);
      totalInterest = roundCurrency(totalInterest + interest);
      totalPaid = roundCurrency(totalPaid + minimumPayment);
      monthInterest = roundCurrency(monthInterest + interest);
      monthPaid = roundCurrency(monthPaid + minimumPayment);

      monthRows.push({
        monthIndex: monthIndex + 1,
        monthLabel: monthLabel(monthDate),
        debtId: debt.id,
        debtName: debt.name,
        strategy,
        startingBalance,
        interest,
        payment: minimumPayment,
        endingBalance: roundCurrency(Math.max(0, debt.currentBalance)),
        status: debt.currentBalance <= EPSILON ? "Paid off" : "Active"
      });
    }

    while (extraRemaining > EPSILON) {
      const target = sortDebts(
        debtState.filter((debt) => debt.currentBalance > EPSILON),
        strategy
      )[0];
      if (!target) {
        break;
      }

      const appliedExtra = roundCurrency(Math.min(target.currentBalance, extraRemaining));
      if (appliedExtra <= EPSILON) {
        break;
      }

      target.currentBalance = roundCurrency(target.currentBalance - appliedExtra);
      target.totalPaid = roundCurrency(target.totalPaid + appliedExtra);
      totalPaid = roundCurrency(totalPaid + appliedExtra);
      monthPaid = roundCurrency(monthPaid + appliedExtra);
      extraRemaining = roundCurrency(extraRemaining - appliedExtra);

      const targetRow = monthRows.find((row) => row.debtId === target.id);
      if (targetRow) {
        targetRow.payment = roundCurrency(targetRow.payment + appliedExtra);
        targetRow.endingBalance = roundCurrency(Math.max(0, target.currentBalance));
        targetRow.status = target.currentBalance <= EPSILON ? "Paid off" : "Active";
      }
    }

    for (const debt of debtState) {
      if (debt.currentBalance <= EPSILON) {
        debt.currentBalance = 0;
        if (debt.paidOffMonth === null) {
          debt.paidOffMonth = monthIndex + 1;
          payoffOrder.push({
            debtId: debt.id,
            debtName: debt.name,
            monthIndex: debt.paidOffMonth
          });
        }
      }
    }

    const totalEndingBalance = roundCurrency(debtState.reduce((sum, debt) => sum + debt.currentBalance, 0));
    monthlyTotals.push({
      monthIndex: monthIndex + 1,
      monthLabel: monthLabel(monthDate),
      totalStartingBalance,
      totalEndingBalance,
      interest: monthInterest,
      payment: monthPaid
    });

    schedule.push(
      ...monthRows.map((row) => ({
        ...row,
        endingBalance: roundCurrency(row.endingBalance)
      }))
    );

    if (totalEndingBalance >= totalStartingBalance - EPSILON) {
      stalledMonths += 1;
    } else {
      stalledMonths = 0;
    }

    if (stalledMonths >= 3) {
      return {
        title,
        strategy,
        strategyLabel: createStrategyLabel(strategy),
        summary: {
          totalDebt: roundCurrency(normalizedDebts.reduce((sum, debt) => sum + debt.balance, 0)),
          monthsToPayoff: monthIndex + 1,
          totalInterest,
          totalPaid,
          totalMinimums: roundCurrency(normalizedDebts.reduce((sum, debt) => sum + debt.minimumPayment, 0)),
          extraPayment: normalizedExtra,
          monthlyPayment: roundCurrency(
            normalizedDebts.reduce((sum, debt) => sum + debt.minimumPayment, 0) + normalizedExtra
          ),
          projectedPayoffDateLabel: "Plan needs a larger payment",
          projectedPayoffDate: null,
          payoffOrder,
          firstTarget: baseOrder[0]?.name ?? null,
          fastestWinMonths: payoffOrder[0]?.monthIndex ?? 0
        },
        debts: debtState,
        monthlyTotals,
        schedule,
        status: "stalled"
      };
    }
  }

  const monthsToPayoff = monthlyTotals.length;
  const payoffDate = monthsToPayoff > 0 ? addMonths(simulationStart, monthsToPayoff - 1) : simulationStart;

  return {
    title,
    strategy,
    strategyLabel: createStrategyLabel(strategy),
    summary: {
      totalDebt: roundCurrency(normalizedDebts.reduce((sum, debt) => sum + debt.balance, 0)),
      monthsToPayoff,
      totalInterest,
      totalPaid,
      totalMinimums: roundCurrency(normalizedDebts.reduce((sum, debt) => sum + debt.minimumPayment, 0)),
      extraPayment: normalizedExtra,
      monthlyPayment: roundCurrency(
        normalizedDebts.reduce((sum, debt) => sum + debt.minimumPayment, 0) + normalizedExtra
      ),
      projectedPayoffDateLabel: monthLabel(payoffDate),
      projectedPayoffDate: payoffDate,
      payoffOrder,
      firstTarget: baseOrder[0]?.name ?? null,
      fastestWinMonths: payoffOrder[0]?.monthIndex ?? 0
    },
    debts: debtState.map((debt) => ({
      ...debt,
      progress: debt.balance > 0 ? roundCurrency(((debt.balance - debt.currentBalance) / debt.balance) * 100) : 100
    })),
    monthlyTotals,
    schedule,
    status: "complete"
  };
}

export function createComparisons(planInput) {
  const snowball = solvePayoffPlan({ ...planInput, strategy: "snowball" });
  const avalanche = solvePayoffPlan({ ...planInput, strategy: "avalanche" });
  const custom = solvePayoffPlan({ ...planInput, strategy: "custom" });
  const accelerated = solvePayoffPlan({
    ...planInput,
    extraPayment: roundCurrency((Number(planInput.extraPayment) || 0) + 150)
  });

  return {
    snowball,
    avalanche,
    custom,
    accelerated
  };
}

export function createChartPath(monthlyTotals) {
  if (!monthlyTotals.length) {
    return "M 0 100";
  }

  const maxBalance = Math.max(...monthlyTotals.map((point) => point.totalStartingBalance));
  const width = 560;
  const height = 160;
  const step = monthlyTotals.length === 1 ? width : width / (monthlyTotals.length - 1);

  const points = monthlyTotals.map((point, index) => {
    const x = roundCurrency(index * step);
    const y = roundCurrency(height - (point.totalEndingBalance / maxBalance) * (height - 12) - 6);
    return `${index === 0 ? "M" : "L"} ${x} ${y}`;
  });

  return points.join(" ");
}

export function reorderCustomDebts(debts, targetId, direction) {
  const ordered = debts
    .map((debt, index) => ({ ...debt, customRank: Number(debt.customRank) || index + 1 }))
    .sort((left, right) => left.customRank - right.customRank);

  const index = ordered.findIndex((debt) => debt.id === targetId);
  if (index < 0) {
    return ordered;
  }

  const swapIndex = direction === "up" ? index - 1 : index + 1;
  if (swapIndex < 0 || swapIndex >= ordered.length) {
    return ordered;
  }

  const clone = [...ordered];
  [clone[index], clone[swapIndex]] = [clone[swapIndex], clone[index]];

  return clone.map((debt, orderIndex) => ({
    ...debt,
    customRank: orderIndex + 1
  }));
}
