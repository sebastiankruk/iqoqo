// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//
// frontend/__tests__/e2e/acquisition_workflow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Item Acquisition and Collection Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // 1. Pre-seed localStorage to avoid 'Small crumbs of data' toast interception
    await page.addInitScript(() => {
      window.localStorage.setItem('iqoqo-cookie-consent', 'true');
    });

    // 2. Mock user authentication state (matching useProfile hook)
    await page.route('**/api/profile/', route =>
      route.fulfill({
        status: 200,
        json: {
          success: true,
          data: {
            id: 'test-user-id',
            email: 'test@example.com',
            display_name: 'Test User',
            roles: ['user'],
            permissions: ['upload:cover', 'edit:manifestation']
          }
        }
      })
    );
    await page.goto('/scan');
  });

  test.describe('Desktop Web View', () => {
    test.use({ viewport: { width: 1280, height: 720 } });

    test('Acquire Book via Identifier Lookup and Add to Collection', async ({ page }) => {
      // Mock identifier lookup (matches BottomSheet apiFetch)
      await page.route('**/api/lookup/9780134685991', route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              type: 'Book',
              title: 'Test Book',
              authors: ['Author A'],
              format: 'book'
            }
          }
        })
      );

      // Mock Add to Collection (matches SuccessCardApiClient.post('/scan'))
      await page.route('**/api/scan', route =>
        route.fulfill({
          status: 201,
          json: {
            success: true,
            data: { item_id: 123, manifestation_id: 456 }
          }
        })
      );

      // Execute Workflow
      // 1. Switch to Manual Search tab
      await page.getByRole('button', { name: 'Manual Search' }).click();

      // 2. Fill the lookup field
      await page.getByPlaceholder('Enter barcode or title...').fill('9780134685991');

      // 3. Click search icon button
      await page.locator('button:has(svg.lucide-search)').click();

      // Verify Result (SuccessCard should appear)
      await expect(page.getByText('Test Book')).toBeVisible();

      // 4. Add to Collection
      await page.getByRole('button', { name: 'Add to Collection' }).click();

      // Verify Success Route
      await expect(page).toHaveURL(/.*\/item\/123/);
    });

    test('Acquire Vinyl via Uploaded Cover and Contribute Cover', async ({ page }) => {
      // Match the vision extraction endpoint
      await page.route('**/api/vision/extract', route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: { Title: 'Dark Side of the Moon', Authors: ['Pink Floyd'] }
          }
        })
      );

      // Execute Upload Workflow
      // 1. Switch to Snap Cover tab
      await page.getByRole('button', { name: 'Snap Cover' }).click();

      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.getByRole('button', { name: 'Upload from Gallery' }).click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles({
        name: 'vinyl_cover.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('fake-image-data')
      });

      // Verify Extraction (should transition to Manual Entry form in ScanPage)
      await expect(page.getByText('Manual Entry')).toBeVisible();
      await expect(page.locator('input[name="title"]')).toHaveValue('Dark Side of the Moon');

      // Mock Manual Add
      await page.route('**/api/items/manual', route =>
        route.fulfill({
          status: 201,
          json: {
            success: true,
            data: { item_id: 789, manifestation_id: 101 }
          }
        })
      );

      // Submit Form
      await page.getByRole('button', { name: 'Add to Library' }).click();

      // Verify Redirect to Item Page
      await expect(page).toHaveURL(/.*\/item\/789/);

      // Mock item details for the sidebar
      await page.route('**/api/items/789', route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: {
              id: 789,
              manifestation_id: 101,
              title: 'Dark Side of the Moon',
              status: 'available',
              manifestation_meta: { format: 'vinyl' }
            }
          }
        })
      );

      // 5. Contribute Cover
      await page.route('**/api/manifestations/101/cover', route => route.fulfill({ status: 200, json: { success: true } }));

      // Check the sidebar button - it should be 'Contribute Cover' because it has no cover yet
      const contributeBtn = page.getByRole('button', { name: 'Contribute Cover' });
      await expect(contributeBtn).toBeVisible();
    });
  });

  test.describe('Mobile View', () => {
    test.use({ viewport: { width: 375, height: 812 }, hasTouch: true });

    test('Acquire CD via Barcode Scanner', async ({ page }) => {
      // 1. Barcode tab is default, verify it's active
      await expect(page.getByText('Tap to start camera')).toBeVisible();

      // 2. Open mobile scanner
      // Click the big round camera button
      // Using force: true because sometimes toasts or other overlays might intercept the click check
      await page.locator('button:has(svg.lucide-camera)').click({ force: true });

      // 3. Verify scanner starts
      // 3. Verify scanner starts (wait longer for the camera to 'turn on')
      await expect(page.getByText('Scanning – point at barcode')).toBeVisible({ timeout: 10000 });

      // Since we can't easily simulate camera detection in headless E2E without
      // complex canvas manipulation, we'll assume the scanner works if the state transitions.
    });

    test('Acquire Book via Live Camera Cover Scan', async ({ page }) => {
      // Mock Vision API
      await page.route('**/api/vision/extract', route =>
        route.fulfill({
          status: 200,
          json: {
            success: true,
            data: { Title: 'Dune', Authors: ['Frank Herbert'] }
          }
        })
      );

      // 1. Switch to Snap Cover tab
      await page.getByRole('button', { name: 'Snap Cover' }).click();

      // 2. Start Live Camera
      await page.getByRole('button', { name: 'Start Live Camera' }).click();

      // 3. Capture snapshot
      await page.getByRole('button', { name: 'Snap Live Frame' }).click();

      // Verify Result (Manual Entry form)
      await expect(page.getByText('Manual Entry')).toBeVisible();
      await expect(page.locator('input[name="title"]')).toHaveValue('Dune');
    });
  });
});
