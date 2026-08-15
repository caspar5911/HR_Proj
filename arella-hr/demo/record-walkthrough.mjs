// ─────────────────────────────────────────────────────────────────────────────
// Arella HR — full product walkthrough video recording
//
// Drives the locally running app (http://localhost:5173) with a headless
// Chromium, overlays a caption bar on every step, and records the result:
//
//   1. demo/videos/*.webm        (raw Playwright recording)
//   2. demo/arella-hr-walkthrough.mp4  (H.264, ready to share)
//
// The tour covers both sides of the product:
//   Admin/manager:  dashboard (KPIs + charts + team calendar + activity),
//                   notification center, directory search & filters,
//                   employee profile, org chart, leave approvals, payroll
//                   run processing, team attendance (hours, overtime,
//                   per-employee drill-down), and performance reviews
//                   (cycle progress, writing a review, sharing one).
//   Employee:       "My Home" self-service (balances, pay history, printable
//                   payslip), notification bell, the employee-scoped leave
//                   page, "My Time" (clock in/out + monthly time log), and
//                   "My Reviews" (the shared mid-year review).
//
// Prereqs:
//   - Docker Compose stack is up (db + backend on :8010 + frontend on :5173)
//   - Demo data is seeded:  docker compose exec backend python /app/seed_demo.py
//   - npm i -D playwright && npx playwright install chromium  (in frontend/)
//
// Run from anywhere:
//   node "C:\...\arella-hr\demo\record-walkthrough.mjs"
//
// The recording mutates demo state (approves/rejects 2 leave requests,
// processes the August payroll run, clocks in the demo employee for today,
// submits a new review for Noa Berg, and shares Liam's submitted review).
// Re-seed afterwards to reset:
//   docker compose exec backend python /app/seed_demo.py
// ─────────────────────────────────────────────────────────────────────────────

import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const VIDEO_DIR = path.join(here, "videos");
const OUT_MP4 = path.join(here, "arella-hr-walkthrough.mp4");
const FFMPEG = "C:/Program Files/ffmpeg-8.0-full_build/bin/ffmpeg.exe";
const BASE = "http://localhost:5173";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ------------------------------------------------------------------ */
/*  Caption bar (injected into the page so it appears in the video)    */
/* ------------------------------------------------------------------ */

async function setCaption(page, text) {
  await page.evaluate((t) => {
    document.body.style.paddingTop = "48px";
    let bar = document.getElementById("demo-caption");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "demo-caption";
      bar.style.cssText = [
        "position:fixed", "top:0", "left:0", "right:0", "z-index:9999",
        "display:flex", "align-items:center", "gap:12px", "height:48px",
        "padding:0 20px", "background:#0f172a", "color:#ffffff",
        "font-family:system-ui,Segoe UI,sans-serif", "font-size:15px",
        "letter-spacing:0.2px", "box-shadow:0 2px 10px rgba(0,0,0,.3)",
      ].join(";");
      bar.innerHTML =
        '<span style="width:10px;height:10px;border-radius:999px;background:#22c55e;flex:none"></span>' +
        '<span id="demo-caption-text" style="font-weight:500"></span>';
      document.body.appendChild(bar);
    }
    document.getElementById("demo-caption-text").textContent = t;
  }, text);
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const navLink = (page, name) =>
  page.locator("aside nav").getByText(name, { exact: true });

async function signIn(page, email, password) {
  await page.locator("#email").click();
  await page.locator("#email").type(email, { delay: 45 });
  await page.locator("#password").click();
  await page.locator("#password").type(password, { delay: 60 });
  await sleep(300);
  await page.getByRole("button", { name: "Sign In" }).click();
}

async function main() {
  fs.mkdirSync(VIDEO_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: VIDEO_DIR, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();
  page.setDefaultTimeout(25000);

  try {
    /* ── 1. Login (admin) ─────────────────────────────────────────── */
    await page.goto(`${BASE}/#/login`, { waitUntil: "domcontentloaded" });
    // Login card's h1 is "Sign in" — "Arella HR" there is a <p> logo line.
    await page.getByRole("heading", { name: "Sign in", level: 1 }).waitFor();
    await setCaption(page, "Welcome to Arella HR — signing in as HR admin");
    await sleep(1200);
    await signIn(page, "admin@example.com", "admin123");

    /* ── 2. Dashboard ─────────────────────────────────────────────── */
    await page.getByRole("heading", { name: "Dashboard", level: 1 }).waitFor();
    await page.getByText("Active Employees").waitFor();
    await setCaption(page, "Dashboard — live KPIs, hiring trend, and the team absence calendar");
    await sleep(7000);

    /* ── Notification bell (admin) ─────────────────────────────────── */
    await setCaption(page, "Notification center — live unread badge in the top bar");
    const bell = page.locator('button[title="Notifications"]');
    await bell.locator("span.bg-rose-500").waitFor();
    await sleep(1200);
    await bell.click();
    const panel = page.locator("div.absolute.right-0.z-40");
    await panel.getByRole("button", { name: "Mark all read" }).waitFor();
    await panel.getByText("New leave request from").first().waitFor();
    await setCaption(page, "Unread items — leave requests, approvals, payroll updates");
    await sleep(4000);
    await panel.getByRole("button", { name: "Mark all read" }).click();
    await bell.locator("span.bg-rose-500").waitFor({ state: "detached" });
    await sleep(800);
    await page.keyboard.press("Escape");
    await sleep(700);

    /* ── 3. Employees: directory + department filter ──────────────── */
    await navLink(page, "Employees").click();
    await page.getByRole("heading", { name: "Employees", level: 1 }).waitFor();
    await page.locator("tr", { hasText: "Jordan Avery" }).waitFor();
    await setCaption(page, "Employees — the team directory");
    await sleep(3000);

    await setCaption(page, "Filtering the directory by department: Engineering");
    // Radix Select triggers are <button role="combobox"> whose placeholder
    // is an inner span — match on visible text, not accessible name.
    const deptSelect = (re) => page.locator('button[role="combobox"]').filter({ hasText: re });
    await deptSelect(/departments/i).click();
    await page.getByRole("option", { name: "Engineering" }).click();
    await sleep(3000);
    await deptSelect("Engineering").click();
    await page.getByRole("option", { name: "All Departments" }).click();
    await sleep(1200);

    /* ── 4. Employee profile via search ───────────────────────────── */
    await setCaption(page, "Searching for Sam Okafor and opening his profile");
    const search = page.getByPlaceholder("Search employees...");
    await search.click();
    await search.type("Sam", { delay: 90 });
    await sleep(2200); // debounce + refetch
    await page.getByRole("link", { name: "Sam Okafor" }).click();
    await page.getByRole("heading", { name: /Sam Okafor/ }).waitFor();
    await setCaption(page, "Employee profile — role, manager, and team at a glance");
    await sleep(5000);

    /* ── 5. Org chart ─────────────────────────────────────────────── */
    await navLink(page, "Org Chart").click();
    await page.getByText("Engineering Director").waitFor();
    await setCaption(page, "Org chart — the full reporting structure");
    await sleep(6000);

    /* ── 6. Leave: approval queue ─────────────────────────────────── */
    await navLink(page, "Leave").click();
    await page.getByRole("heading", { name: "Leave Management", level: 1 }).waitFor();
    await setCaption(page, "Leave management — requests and balances at a glance");
    await sleep(4000);

    await setCaption(page, "Switching to the manager approval queue");
    await page.getByRole("button", { name: /Approval Queue/ }).click();
    await sleep(1600);

    /* ── 7. Approve one request ───────────────────────────────────── */
    await setCaption(page, "Approving Sam Okafor's annual leave request");
    const samRow = page.locator("tr", { hasText: "Sam Okafor" });
    await samRow.locator("button").first().click();
    await samRow.getByText("Approved", { exact: true }).waitFor();
    await sleep(2800);

    /* ── 8. Reject one request ────────────────────────────────────── */
    await setCaption(page, "Rejecting Liam Torres's personal leave request");
    const liamRow = page.locator("tr", { hasText: "Liam Torres" });
    await liamRow.locator("button").nth(1).click();
    await liamRow.getByText("Rejected", { exact: true }).waitFor();
    await sleep(2800);

    /* ── 9. Payroll: review processed July run ────────────────────── */
    await navLink(page, "Payroll").click();
    await page.getByRole("heading", { name: "Payroll & Compensation" }).waitFor();
    await sleep(3000);

    await setCaption(page, "Payroll — reviewing the processed July run");
    const julRow = page.locator("tr", { hasText: "Jul 1, 2026" });
    await julRow.locator('[title="View Entries"]').click();
    await page.getByText("Payroll Entries").waitFor();
    await sleep(5000);
    await page.getByRole("button", { name: "Close" }).click();
    await sleep(900);

    /* ── 10. Payroll: process the August draft run ────────────────── */
    await setCaption(page, "Processing the August draft run");
    const augRow = page.locator("tr", { hasText: "Aug 1, 2026" });
    await augRow.locator('[title="Process Run"]').click();
    // The row's icon button also names itself "Process Run" via its title
    // attribute (ARIA fallback), so scope the confirmation to the dialog.
    await page
      .getByRole("alertdialog")
      .getByRole("button", { name: "Process Run", exact: true })
      .click();
    await augRow.getByText("Processed", { exact: true }).waitFor();
    await sleep(3000);

    /* ── 11. Payroll: entries generated for August ────────────────── */
    await setCaption(page, "Entries generated automatically for August");
    await augRow.locator('[title="View Entries"]').click();
    await page.getByText("Total Net").waitFor();
    await sleep(4500);
    await page.getByRole("button", { name: "Close" }).click();
    await sleep(900);

    /* ── 12. Attendance: team rollup ──────────────────────────────── */
    await navLink(page, "Attendance").click();
    await page.getByRole("heading", { name: "Attendance", level: 1 }).waitFor();
    await page.getByText("Team Members").waitFor();
    await setCaption(page, "Attendance — recorded hours and overtime across the team");
    await sleep(5000);

    /* ── 13. Attendance: per-employee drill-down ──────────────────── */
    await setCaption(page, "Drilling into Sam Okafor's day-by-day entries");
    await page.locator("tr", { hasText: "Sam Okafor" }).click();
    await page.getByText("Sam Okafor — August 2026").waitFor();
    await sleep(5000);

    /* ── 14. Performance: cycle progress ──────────────────────────── */
    await navLink(page, "Performance").click();
    await page.getByRole("heading", { name: "Performance Reviews", level: 1 }).waitFor();
    await page.locator("tr", { hasText: "Sam Okafor" }).waitFor();
    await setCaption(page, "Performance — the mid-year cycle with draft, submitted, and shared reviews");
    await sleep(5000);

    /* ── 15. Performance: write a new review ──────────────────────── */
    await setCaption(page, "Writing a new review — rating, strengths, and development goals");
    await page.getByRole("button", { name: "New review", exact: true }).click();
    await page.getByText("Select an employee", { exact: true }).first().click();
    await page.getByRole("option", { name: /Noa Berg/ }).click();
    await sleep(800);
    await page.getByRole("button", { name: "Rate 4 out of 5" }).click();
    await page.locator("#strengths").fill("Led the design system refresh and unblocked two stalled features.");
    await page.locator("#goals").fill("Mentor a junior designer and ship the onboarding revamp.");
    await sleep(1500);
    await page.getByRole("button", { name: "Submit review", exact: true }).click();
    await page.getByText("Review created").waitFor();
    await page.locator("tr", { hasText: "Noa Berg" }).waitFor();
    await sleep(2500);

    /* ── 16. Performance: open the shared review ──────────────────── */
    await setCaption(page, "Opening Sam's shared review — the one the employee can see");
    const samReviewRow = page.locator("tr", { hasText: "Sam Okafor" });
    await samReviewRow.locator('button[title="View details"]').click();
    await page.getByText("Shared — the employee can see this review").waitFor();
    await sleep(4500);
    await page.keyboard.press("Escape");
    await sleep(800);

    /* ── 17. Performance: share a submitted review ────────────────── */
    await setCaption(page, "Sharing Liam's submitted review with him");
    const liamReviewRow = page.locator("tr", { hasText: "Liam Torres" });
    await liamReviewRow.locator('button[title="Share with employee"]').click();
    await page.getByText("Review shared with the employee").waitFor();
    await liamReviewRow.getByText("Shared", { exact: true }).waitFor();
    await sleep(2500);

    /* ── 18. Sign out ─────────────────────────────────────────────── */
    await setCaption(page, "Signing out to show the employee side");
    await page.locator('button[title="Sign out"]').click();
    await page.locator("#email").waitFor();
    await sleep(1500);

    /* ── 13. Login (employee) ─────────────────────────────────────── */
    await setCaption(page, "Signing in as Sam Okafor — employee self-service");
    await signIn(page, "employee@example.com", "employee123");
    // My Home's h1 is a "Hi {name} 👋" greeting — "My Home" is only the
    // sidebar nav item, so wait for the balances card instead.
    await page.getByText("Leave balances").waitFor();
    await setCaption(page, "My Home — balances, pay history, and requests in one place");
    await sleep(6000);

    /* ── Employee notification bell ────────────────────────────────── */
    await setCaption(page, "Employee side — 'payslip ready' pings land in the same bell");
    await bell.click();
    await panel.getByRole("button", { name: "Mark all read" }).waitFor();
    await panel.getByText(/is ready/).first().waitFor();
    await sleep(4000);
    await page.keyboard.press("Escape");
    await sleep(700);

    /* ── 14. Printable payslip ────────────────────────────────────── */
    await setCaption(page, "Opening the just-processed August payslip — printable");
    await page.getByRole("button", { name: /Payslip/ }).first().click();
    await page.getByText("Print / Save PDF").waitFor();
    await sleep(5000);
    // DialogContent adds its own X close button named "Close" (sr-only span),
    // so "Close" matches twice here — the text button renders first in DOM.
    await page.getByRole("button", { name: "Close", exact: true }).first().click();
    await sleep(900);

    /* ── 15. Employee leave page ──────────────────────────────────── */
    await navLink(page, "My Leave").click();
    await page.getByRole("heading", { name: "Leave Management", level: 1 }).waitFor();
    await page.getByText("Leave Balances").waitFor();
    await setCaption(page, "My Leave — this employee's requests and balances only");
    await sleep(4500);

    /* ── 16. My Time: month log ───────────────────────────────────── */
    await navLink(page, "My Time").click();
    await page.getByRole("heading", { name: "My Time", level: 1 }).waitFor();
    await page.getByText("Total Hours").waitFor();
    await setCaption(page, "My Time — the month's recorded hours at a glance");
    await sleep(4000);

    /* ── 17. My Time: clock in for today ──────────────────────────── */
    await setCaption(page, "Clocking in for today — one click");
    await page.getByRole("button", { name: /Clock In/ }).click();
    await page.getByText(/Clocked in/).waitFor();
    await sleep(4000);

    /* ── 18. My Reviews ───────────────────────────────────────────── */
    await navLink(page, "My Reviews").click();
    await page.getByRole("heading", { name: "My Reviews", level: 1 }).waitFor();
    await page.getByText("Review by").first().waitFor();
    await setCaption(page, "My Reviews — Sam's shared mid-year review, rating, strengths, and goals");
    await sleep(6000);

    /* ── 19. Wrap-up ──────────────────────────────────────────────── */
    await navLink(page, "My Home").click();
    await setCaption(page, "Arella HR — people and payroll, for managers and employees");
    await sleep(5000);
  } finally {
    const video = page.video();
    await context.close();
    await browser.close();
    const webmPath = await video.path();

    console.log(`[record] raw video : ${webmPath}`);
    try {
      execFileSync(
        FFMPEG,
        ["-y", "-loglevel", "error", "-i", webmPath,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         "-preset", "medium", "-an", OUT_MP4],
        { stdio: "inherit" }
      );
      console.log(`[record] MP4 ready : ${OUT_MP4}`);
      fs.rmSync(webmPath, { force: true });
      console.log("[record] cleaned up raw .webm");
    } catch (err) {
      console.error("[record] ffmpeg conversion failed — keep the .webm:", err.message);
    }
  }
}

main().catch((err) => {
  console.error("[record] FAILED:", err);
  process.exit(1);
});
