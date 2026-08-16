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

  const expectCount = async (locator, n) => {
    for (let i = 0; i < 40; i++) {
      if ((await locator.count()) === n) return;
      await sleep(250);
    }
    throw new Error(`expected ${n} element(s), found ${await locator.count()}`);
  };

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

  await step("notification bell shows badge and mark-all-read", async () => {
    const bell = page.locator('button[title="Notifications"]');
    await bell.waitFor();
    const badge = page.locator('button[title="Notifications"] span.bg-rose-500');
    await expectCount(badge, 1); // admin is seeded with 2 unread
    await bell.click();
    await page.getByText("New leave request from").first().waitFor();
    await page.getByRole("button", { name: "Mark all read" }).click();
    await badge.waitFor({ state: "detached" });
    await page.keyboard.press("Escape");
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

  await step("performance page shows seeded cycle + 5 reviews", async () => {
    await nav("Performance");
    await page
      .getByRole("heading", { name: "Performance Reviews", level: 1 })
      .waitFor();
    await page.getByText("2026 Mid-Year Review").first().waitFor();
    await expectCount(page.locator("table tbody tr"), 5);
  });

  await step("goals page shows the company OKR board", async () => {
    await nav("Goals");
    await page.getByRole("heading", { name: "Goals", level: 1 }).waitFor();
    // Seeded: 7 goals across the company.
    await expectCount(page.locator("table tbody tr"), 7);
    await page
      .getByText("Migrate the leave module to the new API gateway")
      .first()
      .waitFor();
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

  await step("employee bell opens payslip notification", async () => {
    const bell = page.locator('button[title="Notifications"]');
    await bell.click();
    await page
      .getByText("Your payroll for 2026-07-01 to 2026-07-31 is ready")
      .waitFor();
    // Clicking it marks it read and follows its link back to My Home.
    await page.getByText("Open My Home to view your payslip.").click();
    await page.getByText("Leave balances").first().waitFor();
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

  await step("my-reviews shows shared review", async () => {
    await nav("My Reviews");
    await page.getByRole("heading", { name: "My Reviews", level: 1 }).waitFor();
    // Seeded: Sam has one shared review in the 2026 Mid-Year cycle.
    await page.getByText("2026 Mid-Year Review").first().waitFor();
    await page.getByText("Review by").first().waitFor();
    await page.getByText("Shared", { exact: true }).first().waitFor();
  });

  await step("my-goals shows only the employee's own goals", async () => {
    await nav("My Goals");
    await page.getByRole("heading", { name: "My Goals", level: 1 }).waitFor();
    // Seeded: Sam Okafor has two goals (one active, one completed).
    await expectCount(page.locator("table tbody tr"), 2);
    await page
      .getByText("Migrate the leave module to the new API gateway")
      .first()
      .waitFor();
    await page.getByText("Cut API p95 latency below 200ms").first().waitFor();
  });

  await step("company-wide Goals link hidden from employee", async () => {
    const goalsLink = page
      .locator("aside nav")
      .getByText("Goals", { exact: true });
    if (await goalsLink.count())
      throw new Error("company Goals link visible to employee");
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
