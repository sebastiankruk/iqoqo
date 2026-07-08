import { test, expect } from '@playwright/test';

test.describe('Phase 1 Ingestion Hardening - Allegro Strategy Cascade', () => {

  test.beforeEach(async ({ page }) => {
    // Perform authentication setup or session restoration if required by the instance
    await page.goto('/login');
    await page.fill('input[name="email"]', 'user@iqoqo.local');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/collection');
  });

  test('should successfully ingest an item via Allegro fallback when standard ISBN search yields no results', async ({ page }) => {
    // Intercept backend API call to mock the fallback resolution cascade
    const targetIsbn = '9788301000003';

    await page.route(`**/api/isbn/${targetIsbn}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          title: 'Cascaded Book Title',
          barcode: targetIsbn,
          cover_url: 'http://img.url/cover.jpg',
          description: 'Recovered via downstream pipeline fallback',
          publisher: 'Scientific Publishers',
          source: 'Allegro Catalog',
        }),
      });
    });

    // Navigate to the scan workflow view
    await page.goto('/scan');

    // Open manual entry form modal within the scan view if viewfinder camera is default
    const manualEntryButton = page.locator('button:has-text("Manual Entry"), button:has-text("Wpisz ręcznie")');
    if (await manualEntryButton.isVisible()) {
      await manualEntryButton.click();
    }

    // Input the unindexed target ISBN code
    await page.fill('input[placeholder*="ISBN"], input[name="isbn"]', targetIsbn);
    await page.click('button[type="submit"]:has-text("Scan"), button[type="submit"]:has-text("Skanuj")');

    // Assert that the success card renders with the cascaded metadata fields
    const successCard = page.locator('[data-testid="success-card"]');
    await expect(successCard).toBeVisible({ timeout: 5000 });
    await expect(successCard).toContainText('Cascaded Book Title');

    // Verify source attribution is properly surfaced to the user for validation accountability
    await expect(successCard).toContainText('Allegro Catalog');

    // Confirm that the item can be added cleanly into the user library state
    await page.click('button:has-text("Add to Collection"), button:has-text("Dodaj do kolekcji")');
    await page.waitForURL('**/item/*');

    // Final verification on the item profile page view
    await expect(page.locator('h1')).toContainText('Cascaded Book Title');
  });
});
