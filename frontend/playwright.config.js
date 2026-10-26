import { defineConfig, devices } from "@playwright/test";
import { tmpdir } from "node:os";
import path from "node:path";

const reportDirectory =
  process.env.E2E_REPORT_DIR ||
  path.join(
    tmpdir(),
    "veriq-e2e",
    `${new Date().toISOString().replaceAll(":", "-")}-${process.pid}`,
  );

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  outputDir: path.join(reportDirectory, "artifacts"),
  reporter: [["list"], ["json", { outputFile: path.join(reportDirectory, "results.json") }]],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    ...devices["Desktop Chrome"],
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
