// Debug: drive login -> dashboard -> employees, log console/network/page state.
import { chromium } from "playwright";

const BASE = "http://localhost:5173";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

page.on("console", (m) => console.log(`[console:${m.type()}]`, m.text().slice(0, 300)));
page.on("pageerror", (e) => console.log("[pageerror]", String(e).slice(0, 300)));
page.on("requestfailed", (r) =>
  console.log("[reqfail]", r.method(), r.url(), "-", r.failure()?.errorText)
);
page.on("response", (r) => {
  if (r.status() >= 300 || r.url().includes("/api/"))
    console.log(`[http ${r.status()}]`, r.request().method(), r.url());
});

await page.goto(`${BASE}/#/login`, { waitUntil: "domcontentloaded" });
await page.locator("#email").fill("admin@example.com");
await page.locator("#password").fill("admin123");
await page.getByRole("button", { name: "Sign In" }).click();
await page.getByRole("heading", { name: "Dashboard", level: 1 }).waitFor();
await sleep(5000);

console.log("=== DASHBOARD TEXT ===");
console.log((await page.evaluate(() => document.querySelector("main")?.innerText ?? "?")).slice(0, 900));
console.log("=== DASHBOARD TOKEN KEYS ===");
console.log(await page.evaluate(() => Object.keys(localStorage)));

await page.locator("aside nav").getByText("Employees", { exact: true }).click();
await page.getByRole("heading", { name: "Employees", level: 1 }).waitFor();
await sleep(10000);

console.log("=== EMPLOYEES TEXT ===");
console.log((await page.evaluate(() => document.querySelector("main")?.innerText ?? "?")).slice(0, 900));
console.log("=== ROW COUNT ===", await page.locator("tbody tr").count());

await context.close();
await browser.close();
