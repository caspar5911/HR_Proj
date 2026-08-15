// Probe: verify employee my-home + leave no longer 403, and manager dashboard
// team calendar still works after the team-schedule role gate.
import { chromium } from "playwright";

const BASE = "http://localhost:5173";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function login(page, email, pw) {
  await page.goto(`${BASE}/#/login`, { waitUntil: "domcontentloaded" });
  await page.locator("#email").waitFor({ timeout: 60000 });
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(pw);
  await page.getByRole("button", { name: "Sign In" }).click();
  await sleep(4000);
}

function wire(page, errors) {
  page.setDefaultTimeout(60000);
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("response", (r) => {
    if (r.status() >= 400) errors.push(`http${r.status()}: ${r.url().replace(BASE, "")}`);
  });
}

async function newPage(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  return { context, page };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const errors = [];

  // ── employee ──
  let { page } = await newPage(browser);
  wire(page, errors);
  await login(page, "employee@example.com", "employee123");
  console.log("[employee] landed:", page.url().replace(BASE, ""));

  await page.goto(`${BASE}/#/my-home`, { waitUntil: "domcontentloaded" });
  await sleep(3500);
  const myHome = (await page.locator("body").innerText()).slice(0, 400);
  console.log("[employee] my-home OK, text:\n" + myHome.split("\n").slice(0, 8).join("\n"));

  await page.goto(`${BASE}/#/leave`, { waitUntil: "domcontentloaded" });
  await sleep(3500);
  const leaveText = (await page.locator("body").innerText());
  console.log("[employee] leave page headings:", leaveText.split("\n").filter((l) => l.trim()).slice(0, 10).join(" | "));

  // employee hitting a staff-only page should redirect, not crash
  await page.goto(`${BASE}/#/employees`, { waitUntil: "domcontentloaded" });
  await sleep(2500);
  console.log("[employee] /employees redirected to:", page.url().replace(BASE, ""));
  await page.context().close();

  // ── manager ──
  ({ page } = await newPage(browser));
  wire(page, errors);
  await login(page, "manager@example.com", "manager123");
  console.log("[manager] landed:", page.url().replace(BASE, ""));
  await page.goto(`${BASE}/#/`, { waitUntil: "domcontentloaded" });
  await sleep(4000);
  const dashText = (await page.locator("body").innerText());
  console.log("[manager] dashboard has 'Team calendar':", /team calendar|absence/i.test(dashText));
  console.log("[manager] dashboard has 'Headcount':", /headcount/i.test(dashText));

  // employee profile with manager line
  await page.goto(`${BASE}/#/employees/2`, { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const profText = (await page.locator("body").innerText());
  console.log("[manager] profile 2 shows 'Sam Okafor':", profText.includes("Sam Okafor"));
  console.log("[manager] profile 2 shows a manager name:", /Reports to/i.test(profText) || /Maya/i.test(profText));
  await page.context().close();

  console.log("\n[probe] errors:", errors.length ? "" : "(none)");
  errors.forEach((e) => console.log("  -", e.slice(0, 200)));
  await browser.close();
  process.exitCode = errors.length ? 1 : 0;
}

main().catch((e) => { console.error("[probe] crashed:", e); process.exit(1); });
