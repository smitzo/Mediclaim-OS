import { expect, test, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import fixture from "../public/demo/sample-claim.json";

const selectSample = (page: Page) => page.getByRole("button", { name: "Select demo PDF:" , exact: false }).click();
async function runSample(page: Page) {
  await selectSample(page);
  await page.getByRole("button", { name: "Run demo", exact: true }).click();
  await expect(page.getByText("Complete", { exact: true })).toBeVisible();
}

test("runs the matching sample without any backend request or browser error", async ({ page }) => {
  const errors: string[] = [];
  const apiRequests: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => { if (new URL(request.url()).pathname.startsWith("/api/")) apiRequests.push(request.url()); });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Run demo", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Export JSON" })).toHaveCount(0);
  await expect(page.getByText("From PDF to structured data", { exact: true })).toBeVisible();
  await runSample(page);
  await expect(page.getByRole("region", { name: "Patient & policy", exact: true })).toContainText("Aarya Mehta");
  await expect(page.getByRole("region", { name: "Discharge summary", exact: true })).toContainText("12 Oct 2026");
  await expect(page.getByRole("table")).toContainText("₹48,500");
  await expect(page.getByRole("status")).toContainText("One claim and three pages loaded");
  await expect(page.getByText("Uses prepared sample results.")).toBeVisible();
  await expect(page.getByRole("img", { name: /Claim form, page 1/ })).toBeVisible();
  expect(errors).toEqual([]);
  expect(apiRequests).toEqual([]);
});

test("source references navigate to the matching page and zoom resets", async ({ page }) => {
  await page.goto("/");
  await runSample(page);
  await page.getByRole("button", { name: "View source page 2 for discharge summary" }).click();
  await expect(page.getByLabel("Page", { exact: true })).toHaveValue("2");
  await expect(page.getByRole("button", { name: "View page 2: Discharge" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("img", { name: /Discharge, page 2/ })).toBeVisible();
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Reset zoom" })).toHaveText("125%");
  await page.getByRole("button", { name: "View source page 3 for itemized bill" }).click();
  await expect(page.getByLabel("Page", { exact: true })).toHaveValue("3");
  await expect(page.getByRole("link", { name: "Open PDF at page 3 in a new tab" })).toHaveAttribute("href", /#page=3$/);
  await page.getByRole("button", { name: "Reset demo", exact: true }).click();
  await expect(page.getByLabel("Page", { exact: true })).toHaveValue("1");
  await expect(page.getByRole("button", { name: "Reset zoom" })).toHaveText("100%");
  await expect(page.getByRole("button", { name: "Run demo", exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Export JSON" })).toHaveCount(0);
});

test("keyboard tabs and exports preserve the exact displayed result and original PDF", async ({ page }) => {
  await page.goto("/");
  await runSample(page);
  const summary = page.getByRole("tab", { name: "Summary", exact: true });
  await summary.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "JSON", exact: true })).toBeFocused();
  await expect(page.getByRole("tabpanel")).toContainText('"result_source": "prepared_sample"');
  await page.keyboard.press("Home");
  await expect(summary).toBeFocused();
  const jsonDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  const downloaded = await jsonDownload;
  expect(downloaded.suggestedFilename()).toBe(`${fixture.result.claim_id}-result.json`);
  expect(JSON.parse(await readFile((await downloaded.path())!, "utf8"))).toEqual(fixture.result);
  const pdfDownload = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download sample PDF", exact: true }).click();
  const pdf = await pdfDownload;
  expect(pdf.suggestedFilename()).toBe(fixture.filename);
  const pdfBytes = await readFile((await pdf.path())!);
  expect(pdfBytes.subarray(0, 5).toString()).toBe("%PDF-");
  expect(pdfBytes).toEqual(await readFile("public/demo/sample-medical-claim.pdf"));
});

test("reset cancels pending results and permits a fresh run", async ({ page }) => {
  let release!: () => void;
  let requested!: () => void;
  let finished!: () => void;
  let first = true;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const started = new Promise<void>((resolve) => { requested = resolve; });
  const served = new Promise<void>((resolve) => { finished = resolve; });
  await page.route("**/demo/sample-claim.json", async (route) => {
    if (first) {
      first = false;
      requested();
      await gate;
      await route.fulfill({ json: fixture }).catch(() => {});
      finished();
    } else await route.fulfill({ json: fixture });
  });
  await page.goto("/");
  await selectSample(page);
  await page.getByRole("button", { name: "Run demo", exact: true }).click();
  await started;
  await expect(page.getByRole("button", { name: "Loading sample…" })).toBeDisabled();
  await page.getByRole("button", { name: "Reset demo", exact: true }).click();
  release();
  await served;
  await expect(page.getByText("From PDF to structured data", { exact: true })).toBeVisible();
  await expect(page.getByText("Complete", { exact: true })).toHaveCount(0);
  await runSample(page);
});

const failures = [
  { name: "missing PDF", path: "**/demo/sample-medical-claim.pdf", status: 404, body: "missing" },
  { name: "missing results", path: "**/demo/sample-claim.json", status: 404, body: "missing" },
  { name: "invalid PDF", path: "**/demo/sample-medical-claim.pdf", status: 200, body: "<html>not a PDF</html>" },
  { name: "malformed JSON", path: "**/demo/sample-claim.json", status: 200, body: "{" },
  { name: "mismatched claim", path: "**/demo/sample-claim.json", status: 200, body: JSON.stringify({ ...fixture, result: { ...fixture.result, claim_id: "WRONG" } }) },
];
for (const failure of failures) {
  test(`recovers from ${failure.name} without displaying success`, async ({ page }) => {
    await page.route(failure.path, (route) => route.fulfill({ status: failure.status, body: failure.body, contentType: "application/json" }));
    await page.goto("/");
    await selectSample(page);
    await page.getByRole("button", { name: "Run demo", exact: true }).click();
    await expect(page.getByRole("main").getByRole("alert")).toBeVisible();
    await expect(page.getByText("Complete", { exact: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Export JSON" })).toHaveCount(0);
    await page.unroute(failure.path);
    await page.getByRole("button", { name: "Try demo again", exact: true }).click();
    await expect(page.getByText("Complete", { exact: true })).toBeVisible();
  });
}

test("a failed page preview offers the original PDF and can be retried", async ({ page }) => {
  await page.route("**/demo/page-1.png*", (route) => route.fulfill({ status: 404 }));
  await page.goto("/");
  await expect(page.getByText("Page preview unavailable.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open the original PDF" })).toHaveAttribute("href", /#page=1$/);
  await page.unroute("**/demo/page-1.png*");
  await page.getByRole("button", { name: "Retry preview" }).click();
  await expect(page.getByRole("img", { name: /Claim form, page 1/ })).toBeVisible();
});

test("narrow screens and JSON stay within the page width", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto("/");
  const noOverflow = () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
  expect(await noOverflow()).toBe(true);
  await runSample(page);
  expect(await noOverflow()).toBe(true);
  await page.getByRole("tab", { name: "JSON", exact: true }).click();
  expect(await noOverflow()).toBe(true);
});

test("company access remains separate from the public demo", async ({ page }) => {
  await page.route("**/api/**", (route) => route.fulfill({ status: 401, json: { detail: "Not authenticated" } }));
  await page.goto("/");
  await page.getByRole("link", { name: "Company workspace", exact: true }).click();
  await expect(page).toHaveURL(/\/workspace$/);
  await expect(page.getByRole("heading", { name: "Company access", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Try the public demo" }).click();
  await expect(page.getByRole("heading", { name: "Document Processor", exact: true })).toBeVisible();
});
