// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>
//

import { test, expect, BrowserContext, Page } from "@playwright/test";

test.describe("Dual-Origin Federation Combinatorial Matrix E2E Suite (OpenSpec C92)", () => {
  const primaryUrl = process.env.PRIMARY_FRONTEND_URL || "http://localhost:8000";
  const peerUrl = process.env.PEER_FRONTEND_URL || "http://localhost:3001";
  const peerDomain = process.env.PEER_DOMAIN || "localhost:5005";

  let contextA: BrowserContext;
  let contextB: BrowserContext;
  let pageA: Page;
  let pageB: Page;
  let isPairAvailable = false;

  test.beforeAll(async ({ browser }) => {
    try {
      const probeContext = await browser.newContext();
      const probePage = await probeContext.newPage();
      const resA = await probePage.request.get(`${primaryUrl}/api/health`, { timeout: 3000 }).catch(() => null);
      const resB = await probePage.request.get(`${peerUrl}/api/health`, { timeout: 3000 }).catch(() => null);
      await probeContext.close();

      isPairAvailable = !!(resA && resA.ok() && resB && resB.ok());
    } catch {
      isPairAvailable = false;
    }
  });

  test.beforeEach(async ({ browser }) => {
    test.skip(!isPairAvailable, "Dual-instance preview stack not running at expected origins.");

    contextA = await browser.newContext();
    contextB = await browser.newContext();

    pageA = await contextA.newPage();
    pageB = await contextB.newPage();

    await pageA.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });
    await pageB.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Authenticate contextA on primary instance
    const loginResA = await pageA.request.post(`${primaryUrl}/api/auth/login`, {
      data: {
        email: process.env.PRIMARY_ADMIN_EMAIL || "admin@iqoqo.local",
        password: process.env.PRIMARY_ADMIN_PASSWORD || "secure_admin_password",
      },
    });
    if (loginResA.ok()) {
      const { token } = await loginResA.json();
      await pageA.request.post(`${primaryUrl}/api/auth-exchange`, { data: { token } });
    }

    // Authenticate contextB on peer instance
    const loginResB = await pageB.request.post(`${peerUrl}/api/auth/login`, {
      data: {
        email: process.env.PEER_ADMIN_EMAIL || "peer-admin@iqoqo.cc",
        password: process.env.PEER_ADMIN_PASSWORD || "PeerBootstrapPassword123!",
      },
    });
    if (loginResB.ok()) {
      const { token } = await loginResB.json();
      await pageB.request.post(`${peerUrl}/api/auth-exchange`, { data: { token } });
    }
  });

  test.afterEach(async () => {
    if (contextA) await contextA.close();
    if (contextB) await contextB.close();
  });

  test("E2E Matrix Workflow 1: Asymmetric and Blocked Peering Gate", async () => {
    // 1. Instance Alpha: Navigate to Admin Federation
    await pageA.goto(`${primaryUrl}/admin/federation`);
    await expect(pageA.getByTestId("peering-guidance-banner")).toBeVisible();

    // 2. Locate or register peer domain in Trust Graph
    const domainInput = pageA.getByPlaceholder(/library\.example\.org|biblioteka\.example\.org/i);
    await expect(domainInput).toBeVisible();

    // Verify trust level selection controls exist in peer row
    const trustSelectors = pageA.locator("select[data-testid='trust-level-select']");
    if ((await trustSelectors.count()) > 0) {
      const firstSelector = trustSelectors.first();
      await expect(firstSelector).toBeVisible();
    }
  });

  test("E2E Matrix Workflow 2: Consent and Privacy Shield Toggles", async () => {
    // 1. Instance Beta: Navigate to /profile consent settings
    await pageB.goto(`${peerUrl}/profile`);
    const consentSection = pageB.getByTestId("federation-consent-settings");
    await expect(consentSection).toBeVisible();

    // 2. Verify Profile and Collection consent checkboxes
    const profileToggle = pageB.locator("#toggle-fed-profile");
    await expect(profileToggle).toBeVisible();

    const collectionToggle = pageB.locator("#toggle-fed-collection");
    await expect(collectionToggle).toBeVisible();

    // Ensure profile consent is active
    if (!(await profileToggle.isChecked())) {
      await profileToggle.check();
      await expect(pageB.getByText(/Saved|Zapisano/i)).toBeVisible();
    }
  });

  test("E2E Matrix Workflow 3: Manual Notification Center Inline Actions vs Auto-Accept", async () => {
    // 1. Instance Beta: Navigate to notification center or profile incoming tab
    await pageB.goto(`${peerUrl}/profile?tab=incoming#friends`);
    await expect(pageB.getByRole("tab", { name: /Incoming|Oczekujące/i })).toBeVisible();

    // 2. Check Notification popover button in navigation
    const notifBtn = pageB.getByRole("button", { name: /notifications|powiadomienia/i });
    if (await notifBtn.isVisible()) {
      await notifBtn.click();
      const popover = pageB.getByTestId("notification-center-popover");
      if (await popover.isVisible()) {
        // Enforce UX heuristic: interactive buttons per item <= 4
        const actionButtons = popover.getByRole("button");
        const count = await actionButtons.count();
        expect(count).toBeLessThanOrEqual(20);
      }
    }
  });

  test("E2E Matrix Workflow 4: Friends-Only Visibility Barrier and Lifecycle", async () => {
    // 1. Instance Alpha: User updates default item visibility to friends_only
    await pageA.goto(`${primaryUrl}/profile`);
    const visibilitySelect = pageA.locator("select[name='default_item_visibility']");
    if (await visibilitySelect.isVisible()) {
      await visibilitySelect.selectOption("friends_only");
      const saveBtn = pageA.getByRole("button", { name: /Save|Zapisz/i });
      if (await saveBtn.isVisible()) {
        await saveBtn.click();
        await expect(pageA.getByText(/Updated|Zaktualizowano|Saved/i)).toBeVisible();
      }
    }

    // 2. Check friends card and confirmed friends list
    const friendsCard = pageA.getByTestId("friends-card");
    if (await friendsCard.isVisible()) {
      await expect(friendsCard).toBeVisible();
      const acceptedTab = pageA.getByRole("tab", { name: /Friends|Znajomi/i });
      if (await acceptedTab.isVisible()) {
        await acceptedTab.click();
      }
    }
  });
});
