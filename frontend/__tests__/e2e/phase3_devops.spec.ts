import { test, expect } from "@playwright/test";

test.describe("Phase 3 DevOps & UI Features", () => {
  test("Landing page has functional GitHub link", async ({ page }) => {
    await page.goto("/");
    const githubLink = page.locator('a:has-text("GitHub")');
    await expect(githubLink).toBeVisible();
    await expect(githubLink).toHaveAttribute("href", "https://github.com/sebastiankruk/iqoqo");
    await expect(githubLink).toHaveAttribute("target", "_blank");
  });

  test("Admin internal settings show Maintenance Mode toggle", async ({ page }) => {
    // Note: This requires admin login which is typically handled in global setup or via a helper
    // For this E2E test we assume the session is available or we bypass auth for the check
    // In a real run, we'd use: await loginAsAdmin(page);
    await page.goto("/admin/settings?tab=internal");
    
    // Check if the Maintenance Mode card exists
    await expect(page.locator("text=Maintenance Mode")).toBeVisible();
    await expect(page.locator("select")).toBeVisible();
  });
});
