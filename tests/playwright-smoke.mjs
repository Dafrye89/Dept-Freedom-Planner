import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { chromium, devices } from "playwright";

const projectRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const artifactDir = path.join(projectRoot, "output", "playwright");
const baseUrl = "http://127.0.0.1:8011";
const pythonExec =
  process.platform === "win32"
    ? path.join(projectRoot, ".venv", "Scripts", "python.exe")
    : path.join(projectRoot, ".venv", "bin", "python");

await mkdir(artifactDir, { recursive: true });

const paidSetupCode = `
from accounts.models import CustomUser
from plans.services import create_saved_plan_from_draft

user, created = CustomUser.objects.get_or_create(
    username="paidsmoke",
    defaults={"email": "paidsmoke@example.com"},
)
user.email = "paidsmoke@example.com"
user.set_password("Freedom_12345")
user.save()
access = user.subscription_access
access.activate_paid("Playwright smoke test")
if not user.debt_plans.filter(is_archived=False).exists():
    create_saved_plan_from_draft(
        user=user,
        draft={
            "title": "Paid Smoke Plan",
            "household_name": "Paid Test Household",
            "strategy_type": "avalanche",
            "extra_monthly_payment": "250.00",
            "debts": [
                {
                    "name": "Freedom Card",
                    "lender_name": "Liberty Bank",
                    "balance": "2400.00",
                    "apr": "21.00",
                    "minimum_payment": "90.00",
                    "due_day": 5,
                    "notes": "",
                    "custom_order": 1,
                },
                {
                    "name": "Truck Note",
                    "lender_name": "Patriot Credit",
                    "balance": "7800.00",
                    "apr": "6.90",
                    "minimum_payment": "295.00",
                    "due_day": 18,
                    "notes": "",
                    "custom_order": 2,
                },
            ],
        },
    )
print("paid smoke user ready")
`.trim();

const bootstrap = () => {
  execFileSync(pythonExec, ["manage.py", "bootstrap_superuser"], {
    cwd: projectRoot,
    stdio: "inherit",
  });
  execFileSync(pythonExec, ["manage.py", "shell", "-c", paidSetupCode], {
    cwd: projectRoot,
    stdio: "inherit",
  });
};

const waitForServer = async (url, timeoutMs = 30000) => {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch (error) {
      // Ignore until timeout.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for ${url}`);
};

bootstrap();

const server = spawn(pythonExec, ["manage.py", "runserver", "127.0.0.1:8011", "--noreload"], {
  cwd: projectRoot,
  stdio: "inherit",
});

await waitForServer(`${baseUrl}/`);

const browser = await chromium.launch({ headless: true });

const fillPlanner = async (page) => {
  await page.goto(`${baseUrl}/planner/start/`, { waitUntil: "networkidle" });
  await page.fill('input[name="details-title"]', "Playwright Guided Plan");
  await page.fill('input[name="details-household_name"]', "Patriotic Household");
  await page.fill('input[name="debts-0-name"]', "Visa Card");
  await page.fill('input[name="debts-0-balance"]', "4200");
  await page.fill('input[name="debts-0-apr"]', "22.5");
  await page.fill('input[name="debts-0-minimum_payment"]', "120");
  await page.fill('input[name="debts-0-custom_order"]', "2");
  await page.getByRole("button", { name: "Add another debt" }).click();
  await page.getByRole("button", { name: "Add another debt" }).click();
  await page.locator('input[name="debts-2-name"]').waitFor();
  await page.fill('input[name="debts-1-name"]', "Truck Loan");
  await page.fill('input[name="debts-1-balance"]', "9800");
  await page.fill('input[name="debts-1-apr"]', "6.9");
  await page.fill('input[name="debts-1-minimum_payment"]', "315");
  await page.fill('input[name="debts-1-custom_order"]', "3");
  await page.fill('input[name="debts-2-name"]', "Store Card");
  await page.fill('input[name="debts-2-balance"]', "1800");
  await page.fill('input[name="debts-2-apr"]', "18.4");
  await page.fill('input[name="debts-2-minimum_payment"]', "75");
  await page.fill('input[name="debts-2-custom_order"]', "1");

  await Promise.all([
    page.waitForURL("**/planner/strategy/"),
    page.getByRole("button", { name: "Continue to strategy" }).click(),
  ]);
  await page.locator('input[value="custom"]').check();
  await page.fill('input[name="strategy-extra_monthly_payment"]', "350");
  await Promise.all([
    page.waitForURL("**/planner/results/"),
    page.getByRole("button", { name: "Continue to results" }).click(),
  ]);
};

try {
  const desktopContext = await browser.newContext({
    viewport: { width: 1512, height: 1100 },
    colorScheme: "light",
  });
  const page = await desktopContext.newPage();

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(artifactDir, "desktop-home.png"), fullPage: true });
  await expectText(page, "Debt Freedom Planner helps you build a solid, step-by-step roadmap to eliminate your balances and earn your way back to breathing room.");
  await expectText(page, "Start free");

  const freeEmail = `free-smoke-${Date.now()}@example.com`;
  const freeUsername = `freesmoke${Date.now()}`;
  await page.goto(`${baseUrl}/accounts/signup/?next=/planner/start/`, { waitUntil: "networkidle" });
  await page.fill('input[name="email"]', freeEmail);
  await page.fill('input[name="username"]', freeUsername);
  await page.fill('input[name="password1"]', "Freedom_12345");
  await page.fill('input[name="password2"]', "Freedom_12345");
  await Promise.all([
    page.waitForURL("**/planner/start/"),
    page.getByRole("button", { name: "Create account" }).click(),
  ]);
  await fillPlanner(page);
  await expectText(page, "You could be debt-free");
  await page.screenshot({ path: path.join(artifactDir, "desktop-results.png"), fullPage: true });
  await page.getByRole("button", { name: "Save this plan" }).click();
  await page.waitForFunction(() => window.location.pathname.startsWith("/account/settings/"));
  await page.waitForLoadState("networkidle");
  await expectText(page, "upgrade to the Pro plan");
  await page.screenshot({ path: path.join(artifactDir, "desktop-free-plan.png"), fullPage: true });
  await desktopContext.close();

  const paidContext = await browser.newContext({
    viewport: { width: 1512, height: 1100 },
    colorScheme: "light",
  });
  const paidPage = await paidContext.newPage();
  await paidPage.goto(`${baseUrl}/accounts/login/`, { waitUntil: "networkidle" });
  await paidPage.fill('input[name="login"]', "paidsmoke@example.com");
  await paidPage.fill('input[name="password"]', "Freedom_12345");
  await Promise.all([
    paidPage.waitForURL("**/plans/dashboard/"),
    paidPage.getByRole("button", { name: "Log in" }).click(),
  ]);
  await paidPage.getByRole("link", { name: "Open" }).first().click();
  await paidPage.waitForFunction(() => window.location.pathname.startsWith("/plans/"));
  await paidPage.waitForLoadState("networkidle");
  await expectText(paidPage, "Scenario lab");
  await paidPage.fill('input[name="scenario_name"]', "Aggressive Push");
  await paidPage.fill('input[name="extra_monthly_payment"]', "450");
  await paidPage.getByRole("button", { name: "Add scenario" }).click();
  await paidPage.waitForLoadState("networkidle");
  await expectText(paidPage, "Aggressive Push");
  await paidPage.screenshot({ path: path.join(artifactDir, "desktop-paid-scenarios.png"), fullPage: true });
  await paidContext.close();

  const founderContext = await browser.newContext({
    viewport: { width: 1512, height: 1100 },
    colorScheme: "light",
  });
  const founderPage = await founderContext.newPage();
  await founderPage.goto(`${baseUrl}/control-room/`, { waitUntil: "networkidle" });
  await founderPage.fill('input[name="username"]', "dafrye89");
  await founderPage.fill('input[name="password"]', "DafHef_04!");
  await Promise.all([
    founderPage.waitForURL("**/control-room/"),
    founderPage.locator('input[type="submit"]').click(),
  ]);
  await expectText(founderPage, "Debt Freedom Planner Control Room");
  await founderPage.goto(baseUrl, { waitUntil: "networkidle" });
  await expectText(founderPage, "Admin");
  await founderPage.screenshot({ path: path.join(artifactDir, "desktop-founder-home.png"), fullPage: true });
  await founderContext.close();

  const mobileContext = await browser.newContext({
    ...devices["Pixel 7"],
    colorScheme: "light",
  });
  const mobilePage = await mobileContext.newPage();
  await mobilePage.goto(baseUrl, { waitUntil: "networkidle" });
  await mobilePage.getByRole("button", { name: "Open marketing navigation" }).waitFor();
  await expectText(mobilePage, "No one is coming to fix the numbers for you.");
  await mobilePage.screenshot({ path: path.join(artifactDir, "mobile-home.png"), fullPage: true });
  const mobileEmail = `mobile-smoke-${Date.now()}@example.com`;
  const mobileUsername = `mobilesmoke${Date.now()}`;
  await mobilePage.goto(`${baseUrl}/accounts/signup/?next=/planner/start/`, { waitUntil: "networkidle" });
  await mobilePage.fill('input[name="email"]', mobileEmail);
  await mobilePage.fill('input[name="username"]', mobileUsername);
  await mobilePage.fill('input[name="password1"]', "Freedom_12345");
  await mobilePage.fill('input[name="password2"]', "Freedom_12345");
  await Promise.all([
    mobilePage.waitForURL("**/planner/start/"),
    mobilePage.getByRole("button", { name: "Create account" }).click(),
  ]);
  await fillPlanner(mobilePage);
  await mobilePage.screenshot({ path: path.join(artifactDir, "mobile-results.png"), fullPage: true });
  await mobileContext.close();
} finally {
  await browser.close();
  server.kill();
}

async function expectText(page, text) {
  const bodyText = await page.locator("body").innerText();
  assert.match(bodyText, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"));
}
