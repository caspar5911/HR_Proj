// Quick UI state capture: logs in and screenshots every main page.
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "shots");
const BASE = "http://localhost:5173";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  page.setDefaultTimeout(25000);

  await page.goto(`${BASE}/#/login`, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Arella HR", level: 1 }).waitFor();
  await page.screenshot({ path: path.join(OUT, "01-login.png") });

  await page.locator("#email").fill("admin@example.com");
  await page.locator("#password").fill("admin123");
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.getByRole("heading", { name: "Dashboard", level: 1 }).waitFor();
  await sleep(3500);
  await page.screenshot({ path: path.join(OUT, "02-dashboard.png"), fullPage: true });

  const nav = (name) => page.locator("aside nav").getByText(name, { exact: true }).click();
  await nav("Employees");
  await page.getByRole("heading", { name: "Employees", level: 1 }).waitFor();
  await sleep(2500);
  await page.screenshot({ path: path.join(OUT, "03-employees.png"), fullPage: true });

  await nav("Leave");
  await page.getByRole("heading", { name: "Leave Management", level: 1 }).waitFor();
  await sleep(2500);
  await page.screenshot({ path: path.join(OUT, "04-leave.png"), fullPage: true });

  await page.getByRole("button", { name: /Approval Queue/ }).click();
  await sleep(1800);
  await page.screenshot({ path: path.join(OUT, "05-leave-approvals.png"), fullPage: true });

  await nav("Payroll");
  await page.getByRole("heading", { name: "Payroll & Compensation" }).waitFor();
  await sleep(2500);
  await page.screenshot({ path: path.join(OUT, "06-payroll.png"), fullPage: true });

  await browser.close();
  console.log(`[shots] done → ${OUT}`);
}

main().catch((err) => { console.error("[shots] FAILED:", err); process.exit(1); });
