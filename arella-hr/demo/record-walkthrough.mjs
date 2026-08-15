// ─────────────────────────────────────────────────────────────────────────────
// Arella HR — full product walkthrough video recording
//
// Drives the locally running app (http://localhost:5173) with a headless
// Chromium, overlays a caption bar on every step, and records the result:
//
//   1. demo/videos/*.webm        (raw Playwright recording)
//   2. demo/arella-hr-walkthrough.mp4  (H.264, ready to share)
//
// Prereqs:
//   - Docker Compose stack is up (db + backend on :8010 + frontend on :5173)
//   - Demo data is seeded:  docker compose exec backend python /app/seed_demo.py
//   - npm i -D playwright && npx playwright install chromium  (in frontend/)
//
// Run from anywhere:
//   node "C:\...\arella-hr\demo\record-walkthrough.mjs"
//
// The recording mutates demo state (approves/rejects 2 leave requests and
// processes the August payroll run). Re-seed afterwards to reset:
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
    /* ── 1. Login ─────────────────────────────────────────────────── */
    await page.goto(`${BASE}/#/login`, { waitUntil: "domcontentloaded" });
    await page.getByRole("heading", { name: "Arella HR", level: 1 }).waitFor();
    await setCaption(page, "Welcome to Arella HR — signing in");
    await sleep(1500);

    await page.locator("#email").click();
    await page.locator("#email").type("admin@example.com", { delay: 55 });
    await page.locator("#password").click();
    await page.locator("#password").type("admin123", { delay: 80 });
    await sleep(400);
    await page.getByRole("button", { name: "Sign In" }).click();

    /* ── 2. Dashboard ─────────────────────────────────────────────── */
    await page.getByRole("heading", { name: "Dashboard", level: 1 }).waitFor();
    await page.getByText("Active Employees").waitFor();
    await setCaption(page, "Dashboard — live overview of the whole organization");
    await sleep(6000);

    /* ── 3. Employees: directory + search ─────────────────────────── */
    await navLink(page, "Employees").click();
    await page.getByRole("heading", { name: "Employees", level: 1 }).waitFor();
    // List is newest-first (created_at desc) with page_size 10, so the
    // most recently seeded employee (Jordan Avery, id 12) is the first row.
    await page.locator("tr", { hasText: "Jordan Avery" }).waitFor();
    await setCaption(page, "Employees — the team directory");
    await sleep(3500);

    await setCaption(page, "Searching for an employee by name");
    const search = page.getByPlaceholder("Search employees...");
    await search.click();
    await search.type("Maya", { delay: 90 });
    await sleep(1600); // debounce + refetch
    await sleep(2500);
    await search.fill("");
    await sleep(1200);

    /* ── 4. Employees: department filter ──────────────────────────── */
    await setCaption(page, "Filtering the directory by department: Engineering");
    // Radix Select triggers are <button role="combobox"> whose placeholder
    // is an inner span — match on visible text, not accessible name.
    const deptSelect = (re) => page.locator('button[role="combobox"]').filter({ hasText: re });
    await deptSelect(/departments/i).click();
    await page.getByRole("option", { name: "Engineering" }).click();
    await sleep(1400);
    await sleep(3000);
    await deptSelect("Engineering").click();
    await page.getByRole("option", { name: "All Departments" }).click();
    await sleep(1200);

    /* ── 5. Leave: approval queue ─────────────────────────────────── */
    await navLink(page, "Leave").click();
    await page.getByRole("heading", { name: "Leave Management", level: 1 }).waitFor();
    await setCaption(page, "Leave management — requests and balances at a glance");
    await sleep(4000);

    await setCaption(page, "Switching to the manager approval queue");
    await page.getByRole("button", { name: /Approval Queue/ }).click();
    await sleep(1600);

    /* ── 6. Approve one request ───────────────────────────────────── */
    await setCaption(page, "Approving Sam Okafor's annual leave request");
    const samRow = page.locator("tr", { hasText: "Sam Okafor" });
    await samRow.locator("button").first().click();
    await samRow.getByText("Approved", { exact: true }).waitFor();
    await sleep(2800);

    /* ── 7. Reject one request ────────────────────────────────────── */
    await setCaption(page, "Rejecting Liam Torres's personal leave request");
    const liamRow = page.locator("tr", { hasText: "Liam Torres" });
    await liamRow.locator("button").nth(1).click();
    await liamRow.getByText("Rejected", { exact: true }).waitFor();
    await sleep(2800);

    /* ── 8. Payroll: review processed July run ────────────────────── */
    await navLink(page, "Payroll").click();
    await page.getByRole("heading", { name: "Payroll & Compensation" }).waitFor();
    await sleep(3500);

    await setCaption(page, "Payroll — reviewing the processed July run");
    const julRow = page.locator("tr", { hasText: "Jul 1, 2026" });
    await julRow.locator('[title="View Entries"]').click();
    await page.getByText("Payroll Entries").waitFor();
    await sleep(5000);
    await page.getByRole("button", { name: "Close" }).click();
    await sleep(900);

    /* ── 9. Payroll: process the August draft run ─────────────────── */
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

    /* ── 10. Payroll: entries generated for August ────────────────── */
    await setCaption(page, "Entries generated automatically for August");
    await augRow.locator('[title="View Entries"]').click();
    await page.getByText("Total Net").waitFor();
    await sleep(4500);
    await page.getByRole("button", { name: "Close" }).click();
    await sleep(900);

    /* ── 11. Dashboard wrap-up ────────────────────────────────────── */
    await navLink(page, "Dashboard").click();
    await page.getByRole("heading", { name: "Dashboard", level: 1 }).waitFor();
    await setCaption(page, "Back to the dashboard — pending leave and payroll are up to date");
    await sleep(7000);
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
