// Probe: which pages show the sidebar sign-out button (admin + employee)?
import { chromium } from "playwright";

const BASE = "http://localhost:5173";

const ADMIN_PAGES = [
  "/", "/employees", "/org-chart", "/leave", "/payroll",
  "/attendance", "/performance", "/audit-logs", "/goals",
  "/my-home", "/my-time", "/my-reviews",
];
const EMPLOYEE_PAGES = [
  "/my-home", "/leave", "/my-time", "/my-reviews", "/goals",
];

async function checkPage(page, path) {
  await page.goto(`${BASE}/#${path}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1200);
  const btn = page.locator('button[title="Sign out"]');
  const count = await btn.count();
  let inViewport = false;
  if (count) {
    const box = await btn.first().boundingBox();
    inViewport = !!box && box.y >= 0 && box.y + box.height <= 900;
  }
  const scrollHeight = await page.evaluate(
    () => document.documentElement.scrollHeight
  );
  return { path, signout: count, inViewport, tall: scrollHeight > 950 };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  async function signIn(email, password) {
    await page.goto(`${BASE}/#/login`, { waitUntil: "domcontentloaded" });
    await page.locator("#email").fill(email);
    await page.locator("#password").fill(password);
    await page.getByRole("button", { name: "Sign In" }).click();
    await page.getByRole("heading", { name: "Dashboard", level: 1 })
      .or(page.getByText("Leave balances"))
      .waitFor({ timeout: 15000 });
    await page.waitForTimeout(500);
  }

  console.log("── admin ──");
  await signIn("admin@example.com", "admin123");
  for (const p of ADMIN_PAGES) {
    const r = await checkPage(page, p);
    console.log(
      `${r.inViewport ? "IN-VIEW   " : "BELOW-FOLD"} page ${r.tall ? "(tall)" : "(short)"} ${r.path}`
    );
  }

  // sign out via the sidebar button itself (dogfooding the control under test)
  await page.locator('button[title="Sign out"]').click().catch(() => {});
  await page.getByRole("heading", { name: "Sign in", level: 1 }).waitFor();

  console.log("\n── employee ──");
  await signIn("employee@example.com", "employee123");
  for (const p of EMPLOYEE_PAGES) {
    const r = await checkPage(page, p);
    console.log(
      `${r.inViewport ? "IN-VIEW   " : "BELOW-FOLD"} page ${r.tall ? "(tall)" : "(short)"} ${p}`
    );
  }

  await browser.close();
}

main().catch((e) => {
  console.error("probe failed:", e);
  process.exit(1);
});
