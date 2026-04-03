// frontend/__tests__/e2e/acquisition_workflow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Item Acquisition and Collection Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock user authentication state
    await page.route('**/api/v1/auth/me', route => 
      route.fulfill({ status: 200, json: { id: 'test-user-id', role: 'user' } })
    );
    await page.goto('/scan');
  });

  test.describe('Desktop Web View', () => {
    test.use({ viewport: { width: 1280, height: 720 } });

    test('Acquire Book via Identifier Lookup and Add to Collection', async ({ page }) => {
      // Mock ISBN lookup
      await page.route('**/api/v1/scanner/lookup*', route => 
        route.fulfill({ status: 200, json: { type: 'Book', title: 'Test Book', authors: ['Author A'] } })
      );
      await page.route('**/api/v1/collection/items', route => 
        route.fulfill({ status: 201, json: { id: 'new-item-id' } })
      );

      // Execute Workflow
      await page.getByRole('button', { name: /Manual Entry|Lookup/i }).click();
      await page.getByPlaceholder('Enter ISBN, UPC, or identifier').fill('9780134685991');
      await page.getByRole('button', { name: 'Search' }).click();

      // Verify Result and Add to Collection
      await expect(page.getByText('Test Book')).toBeVisible();
      await page.getByRole('button', { name: 'Add to Collection' }).click();
      
      // Verify Success Route
      await expect(page).toHaveURL(/.*\/item\/new-item-id/);
      await expect(page.getByText('Successfully added to your collection')).toBeVisible();
    });

    test('Acquire Vinyl via Uploaded Cover and Contribute Cover', async ({ page }) => {
      // Mock Cover Vision API
      await page.route('**/api/v1/scanner/cover', route => 
        route.fulfill({ status: 200, json: { type: 'LP', title: 'Dark Side of the Moon', artist: 'Pink Floyd' } })
      );

      // Execute Upload Workflow
      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.getByText(/Upload Cover|Select File/i).click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles({
        name: 'vinyl_cover.jpg',
        mimeType: 'image/jpeg',
        buffer: Buffer.from('fake-image-data')
      });

      // Verify Extraction
      await expect(page.getByText('Dark Side of the Moon')).toBeVisible();
      
      // Contribute Cover
      await page.route('**/api/v1/items/*/cover', route => route.fulfill({ status: 200 }));
      await page.getByRole('button', { name: 'Contribute Cover Art' }).click();
      await expect(page.getByText('Cover contributed successfully')).toBeVisible();
    });
  });

  test.describe('Mobile View', () => {
    test.use({ viewport: { width: 375, height: 812 }, hasTouch: true });

    test('Acquire CD via Barcode Scanner', async ({ page }) => {
      // Mock Barcode API
      await page.route('**/api/v1/scanner/barcode*', route => 
        route.fulfill({ status: 200, json: { type: 'CD', title: 'Nevermind', artist: 'Nirvana' } })
      );

      // Open mobile scanner
      await page.getByRole('button', { name: /Scan Barcode/i }).click();
      
      // Simulate successful barcode read from the camera view
      // Since we can't test actual camera hardware, we dispatch a custom event or evaluate 
      // the callback that the barcode scanner library would trigger.
      await page.evaluate(() => {
        window.dispatchEvent(new CustomEvent('barcode-detected', { detail: { code: '020831467129' } }));
      });

      // Verify Result
      await expect(page.getByText('Nevermind')).toBeVisible();
      await expect(page.getByText('CD')).toBeVisible();

      // Add to Collection
      await page.route('**/api/v1/collection/items', route => route.fulfill({ status: 201 }));
      await page.getByRole('button', { name: 'Add to Collection' }).click();
      await expect(page.getByText('Saved')).toBeVisible();
    });

    test('Acquire Book via Live Camera Cover Scan', async ({ page }) => {
      // Mock Cover Vision API
      await page.route('**/api/v1/scanner/cover', route => 
        route.fulfill({ status: 200, json: { type: 'Book', title: 'Dune', authors: ['Frank Herbert'] } })
      );

      // Open live camera view
      await page.getByRole('button', { name: /Scan Cover/i }).click();

      // Simulate capturing an image from the mobile viewfinder
      await page.getByRole('button', { name: 'Capture' }).click();

      // Verify Result
      await expect(page.getByText('Dune')).toBeVisible();
      await expect(page.getByText('Frank Herbert')).toBeVisible();
    });
  });
});
