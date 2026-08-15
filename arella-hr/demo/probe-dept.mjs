import { chromium } from "playwright";
const b = await chromium.launch({ headless: true });
const p = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
p.setDefaultTimeout(20000);
await p.goto("http://localhost:5173/#/login");
await p.locator("#email").fill("admin@example.com");
await p.locator("#password").fill("admin123");
await p.getByRole("button", { name: "Sign In" }).click();
await p.getByRole("heading", { name: "Dashboard", level: 1 }).waitFor();
const nav = (n) => p.locator("aside nav").getByText(n, { exact: true }).click();

// ── Leave page ──
await nav("Leave");
await p.getByRole("heading", { name: "Leave Management", level: 1 }).waitFor();
console.log("Approval Queue btn:", await p.getByRole("button", { name: /Approval Queue/ }).count());
await p.getByRole("button", { name: /Approval Queue/ }).click();
await p.waitForTimeout(1500);
const sam = p.locator("tr", { hasText: "Sam Okafor" });
const liam = p.locator("tr", { hasText: "Liam Torres" });
console.log("Sam row:", await sam.count(), "buttons:", await sam.locator("button").count());
console.log("Liam row:", await liam.count(), "buttons:", await liam.locator("button").count());
console.log("Sam btn titles:", await sam.locator("button").evaluateAll(bts => bts.map(x => x.getAttribute("title"))));
console.log("Liam btn titles:", await liam.locator("button").evaluateAll(bts => bts.map(x => x.getAttribute("title"))));

// ── Payroll page ──
await nav("Payroll");
await p.getByRole("heading", { name: "Payroll & Compensation" }).waitFor();
await p.waitForTimeout(1000);
const jul = p.locator("tr", { hasText: "Jul 1, 2026" });
const aug = p.locator("tr", { hasText: "Aug 1, 2026" });
console.log("Jul row:", await jul.count(), "ViewEntries:", await jul.locator('[title="View Entries"]').count());
console.log("Aug row:", await aug.count(), "ProcessRun:", await aug.locator('[title="Process Run"]').count());
// open July entries (non-mutating) to verify dialog + Total Net
await jul.locator('[title="View Entries"]').click();
await p.getByText("Payroll Entries").waitFor();
console.log("July dialog Total Net:", await p.getByText("Total Net").count());
await p.getByRole("button", { name: "Close" }).click();
await b.close();
console.log("PROBE OK");
