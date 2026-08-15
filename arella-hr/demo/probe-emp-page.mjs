// Probe: log in as admin, open Employees, dump what the DOM actually contains.
import { chromium } from "playwright";

const BASE = "http://localhost:5173";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  page.setDefaultTimeout(60000);

  const errors = [];
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
  page.on("requestfailed", (r) => errors.push(`reqfail: ${r.url()} ${r.failure()?.errorText}`));

  await page.goto(`${BASE}/#/login`, { waitUntil: "domcontentloaded" });
  await page.locator("#email").waitFor({ timeout: 60000 });
  console.log("[probe] login form visible");

  await page.locator("#email").fill("admin@example.com");
  await page.locator("#password").fill("admin123");
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.getByRole("heading", { name: "Dashboard", level: 1 }).waitFor({ timeout: 60000 });
  await sleep(3000);
  console.log("[probe] dashboard visible");

  const sidebar = await page.locator("aside").innerText();
  console.log("[probe] sidebar text:\n" + sidebar);

  await page.locator("aside nav").getByText("Employees", { exact: true }).click();
  await sleep(8000);
  const bodyText = (await page.locator("body").innerText()).slice(0, 800);
  console.log("[probe] employees page body (first 800 chars):\n" + bodyText);
  console.log("[probe] td a count:", await page.locator("td a").count());
  const table = await page.locator("table").count();
  console.log("[probe] table count:", table);
  if (table) {
    const rows = await page.locator("tbody tr").count();
    console.log("[probe] tbody rows:", rows);
    if (rows) console.log("[probe] first row HTML:", (await page.locator("tbody tr").first().innerHTML()).slice(0, 500));
  }

  if (errors.length) {
    console.log("\n[probe] errors:");
    errors.forEach((e) => console.log("  -", e.slice(0, 300)));
  }
  await browser.close();
}

main().catch((e) => { console.error("[probe] crashed:", e); process.exit(1); });
