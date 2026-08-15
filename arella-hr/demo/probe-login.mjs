import { chromium } from "playwright";
const b = await chromium.launch({ headless: true });
const context = await b.newContext({ viewport: { width: 1440, height: 900 } });
const p = await context.newPage();
p.setDefaultTimeout(30000);
p.on("console", (m) => { if (m.type() !== "debug") console.log("[console]", m.type(), m.text().slice(0, 300)); });
p.on("response", (r) => {
  if (r.url().includes("/api/")) {
    let body = "";
    try { body = (r.body() ? "" : ""); } catch {}
    console.log("[net]", r.status(), r.request().method(), r.url().replace("http://localhost:5173", ""));
  }
});
await p.goto("http://localhost:5173/#/login", { waitUntil: "domcontentloaded" });
await p.getByRole("heading", { name: "Arella HR", level: 1 }).waitFor();
console.log("login heading ok");
await p.locator("#email").click();
await p.locator("#email").type("admin@example.com", { delay: 55 });
await p.locator("#password").click();
await p.locator("#password").type("admin123", { delay: 80 });
await new Promise((r) => setTimeout(r, 400));
console.log("email value:", await p.locator("#email").inputValue());
console.log("password len:", (await p.locator("#password").inputValue()).length);
await p.getByRole("button", { name: "Sign In" }).click();
await p.waitForTimeout(8000);
console.log("URL:", p.url());
console.log("localStorage token:", await p.evaluate(() => (localStorage.getItem("access_token") || "").slice(0, 20)));
console.log("PAGE TEXT:", (await p.evaluate(() => document.body.innerText)).slice(0, 500).replace(/\n/g, " | "));
await p.screenshot({ path: "probe-login.png" });
console.log("screenshot saved");
await b.close();
