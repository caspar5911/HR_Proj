// Probe: employee My Home — does the Payslip button render?
import { chromium } from "playwright";

const BASE = "http://localhost:5173";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("response", (r) => {
    if (r.status() >= 400) errors.push(`http${r.status()}: ${r.url().replace(BASE, "")}`);
  });

  await page.goto(`${BASE}/#/login`, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Sign in", level: 1 }).waitFor();
  await page.locator("#email").fill("employee@example.com");
  await page.locator("#password").fill("employee123");
  await page.getByRole("button", { name: "Sign In" }).click();
  await sleep(5000);

  console.log("[probe] url:", page.url().replace(BASE, ""));
  const text = await page.locator("body").innerText();
  console.log("[probe] 'No payslips yet' present:", text.includes("No payslips yet"));
  console.log("[probe] 'Latest pay' present:", text.includes("Latest pay"));
  console.log("[probe] Payslip button count:", await page.getByRole("button", { name: /Payslip/ }).count());
  console.log("--- body text (trimmed) ---");
  console.log(text.split("\n").filter((l) => l.trim()).slice(0, 40).join("\n"));
  console.log("--- errors ---");
  console.log(errors.length ? errors.join("\n") : "(none)");

  await browser.close();
}

main().catch((e) => { console.error("[probe] crashed:", e); process.exit(1); });
