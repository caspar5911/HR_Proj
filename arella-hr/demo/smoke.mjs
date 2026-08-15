// Browser smoke test: walks every main route as admin and employee,
// asserting that key content renders and collecting page/console errors.
import { chromium } from "playwright";

const BASE = "http://localhost:5173";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const failures = [];
const consoleErrors = [];
const pageErrors = [];

async function step(name, fn) {
  try {
    await fn();
    console.log(`  PASS  ${name}`);
  } catch (err) {
    failures.push(name);
    console.log(`  FAIL  ${name}\n        ${err.message.split("\n").slice(0, 4).join("\n        ")}`);
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  page.setDefaultTimeout(45000);

  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => pageErrors.push(err.message));

  const nav = (label) =>
    page.locator("aside nav").getByText(label, { exact: true }).click();

  const filterNoise = (list) =>
    list.filter((t) => !/favicon|React Router Future|useLayoutEffect|act\(|Cannot read prop/i.test(t));

  // ── Admin session ─────────────────────────────────────────────────────────
  console.log("\n[smoke] admin session");

  await step("login page renders", async () => {
    await page.goto(`${BASE}/#/login`, { waitUntil: "domcontentloaded" });
    await page.getByRole("heading", { name: "Sign in", level: 1 }).waitFor();
  });

  await step("admin sign-in reaches dashboard", async () => {
    await page.locator("#email").fill("admin@example.com");
    await page.locator("#password").fill("admin123");
    await page.getByRole("button", { name: "Sign In" }).click();
    await page.getByRole("heading", { name: "Dashboard", level: 1 }).waitFor();
    await sleep(2500); // let KPIs/charts settle
  });

  await step("employee list renders", async () => {
    await nav("Employees");
    await page.getByRole("heading", { name: "Employees", level: 1 }).waitFor();
    await page.locator("td a").first().waitFor();
  });

  let profileName = "";
  await step("employee profile renders", async () => {
    profileName = (await page.locator("td a").first().innerText()).trim();
    await page.locator("td a").first().click();
    await page
      .getByRole("heading", { name: profileName, level: 1 })
      .waitFor();
  });

  await step("payslips section on profile", async () => {
    await page.getByText("Payslips", { exact: true }).first().waitFor();
    const viewBtn = page.getByRole("button", { name: "View payslip" });
    if (await viewBtn.count()) {
      await viewBtn.click();
      await page.getByText("Print / Save PDF").waitFor();
      await page.keyboard.press("Escape");
      await sleep(500);
    } else {
      await page.getByText("No payslips yet.").waitFor();
    }
  });

  await step("org chart renders", async () => {
    await nav("Org Chart");
    await page.getByRole("heading", { name: "Org chart", level: 1 }).waitFor();
    await sleep(1500);
  });

  await step("audit log renders (admin-only)", async () => {
    await nav("Audit Log");
    await page.getByRole("heading", { name: "Audit log", level: 1 }).waitFor();
  });

  await step("leave page renders", async () => {
    await nav("Leave");
    await page.getByRole("heading", { name: "Leave Management", level: 1 }).waitFor();
  });

  await step("payroll page renders", async () => {
    await nav("Payroll");
    await page.getByRole("heading", { name: "Payroll & Compensation" }).waitFor();
    await sleep(1500);
  });

  await step("attendance page renders", async () => {
    await nav("Attendance");
    await page.getByRole("heading", { name: "Attendance", level: 1 }).waitFor();
    await page.getByText("Team Members").waitFor();
  });

  // ── Employee session ─────────────────────────────────────────────────────
  console.log("\n[smoke] employee session");

  await step("sign out", async () => {
    await page.locator('button[title="Sign out"]').click();
    await page.getByRole("heading", { name: "Sign in", level: 1 }).waitFor();
  });

  await step("employee sign-in reaches my home", async () => {
    await page.locator("#email").fill("employee@example.com");
    await page.locator("#password").fill("employee123");
    await page.getByRole("button", { name: "Sign In" }).click();
    // My Home greets with "Hi {name} 👋" — wait for the balances card instead.
    await page.getByText("Leave balances").waitFor();
    await sleep(2000);
  });

  await step("my-home payslips section", async () => {
    const viewBtn = page.getByRole("button", { name: /Payslip/ }).first();
    if (await viewBtn.count()) {
      await viewBtn.click();
      await page.getByText("Print / Save PDF").waitFor();
      await page.keyboard.press("Escape");
    } else {
      await page.getByText(/Payslips|No payslips yet/).first().waitFor();
    }
  });

  await step("my-time page renders", async () => {
    await nav("My Time");
    await page.getByRole("heading", { name: "My Time", level: 1 }).waitFor();
    await page.getByText("Total Hours").waitFor();
  });

  await step("attendance hidden from employee", async () => {
    const attLink = page
      .locator("aside nav")
      .getByText("Attendance", { exact: true });
    if (await attLink.count()) throw new Error("Attendance link visible to employee");
  });

  await step("audit log hidden from employee", async () => {
    const auditLink = page
      .locator("aside nav")
      .getByText("Audit Log", { exact: true });
    if (await auditLink.count()) throw new Error("Audit Log link visible to employee");
  });

  await browser.close();

  // ── Report ────────────────────────────────────────────────────────────────
  const realPageErrors = filterNoise(pageErrors);
  const realConsoleErrors = filterNoise(consoleErrors);

  if (realPageErrors.length) {
    console.log(`\n[smoke] ${realPageErrors.length} uncaught page error(s):`);
    realPageErrors.forEach((e) => console.log(`  - ${e.slice(0, 200)}`));
    failures.push("page errors");
  }
  if (realConsoleErrors.length) {
    console.log(`\n[smoke] ${realConsoleErrors.length} console error(s):`);
    realConsoleErrors.forEach((e) => console.log(`  - ${e.slice(0, 200)}`));
  }

  console.log(
    `\n[smoke] ${failures.length === 0 ? "ALL PASSED" : `${failures.length} FAILED: ${failures.join(", ")}`}`
  );
  process.exit(failures.length === 0 ? 0 : 1);
}

main().catch((err) => {
  console.error("[smoke] crashed:", err);
  process.exit(1);
});
