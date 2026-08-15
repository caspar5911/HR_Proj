// Find which request(s) return 422 during the admin + employee walkthrough.
import { chromium } from "playwright";

const BASE = "http://localhost:5173";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  page.setDefaultTimeout(45000);

  const bad = [];
  page.on("response", async (res) => {
    if (res.status() >= 400) {
      let body = "";
      try { body = (await res.text()).slice(0, 300); } catch { /* ignore */ }
      bad.push(`${res.status()} ${res.request().method()} ${new URL(res.url()).pathname} :: ${body}`);
    }
  });
  page.on("console", (msg) => {
    if (msg.type() === "error" && /422|Unprocessable/.test(msg.text())) console.log("[console]", msg.text());
  });

  // Admin
  await page.goto(`${BASE}/#/login`, { waitUntil: "domcontentloaded" });
  await page.locator("#email").fill("admin@example.com");
  await page.locator("#password").fill("admin123");
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.getByRole("heading", { name: "Dashboard", level: 1 }).waitFor();
  await sleep(3000);
  for (const label of ["Employees", "Org Chart", "Leave", "Payroll", "Attendance", "Performance", "My Home", "My Time", "Audit Log"]) {
    try {
      await page.locator("aside nav").getByText(label, { exact: true }).click();
      await sleep(1200);
    } catch { /* nav not present for this role */ }
  }
  await page.locator('button[title="Sign out"]').click();
  await page.getByRole("heading", { name: "Sign in", level: 1 }).waitFor();

  // Employee
  await page.locator("#email").fill("employee@example.com");
  await page.locator("#password").fill("employee123");
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.getByText("Leave balances").waitFor();
  await sleep(2000);
  for (const label of ["My Leave", "My Time", "My Reviews"]) {
    await page.locator("aside nav").getByText(label, { exact: true }).click();
    await sleep(1200);
  }

  await browser.close();

  if (bad.length === 0) {
    console.log("[find-422] no 4xx/5xx responses seen");
  } else {
    console.log(`[find-422] ${bad.length} error response(s):`);
    bad.forEach((b) => console.log("  -", b));
  }
}

main().catch((err) => { console.error("[find-422] crashed:", err); process.exit(1); });
