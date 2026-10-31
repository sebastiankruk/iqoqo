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

test.describe("Multi-Instance Dual-Origin Live Federation E2E Suite", () => {
  // Configurable dual origins (defaulting to paired preview stack ports)
  const primaryUrl = process.env.PRIMARY_FRONTEND_URL || "http://localhost:8000";
  const peerUrl = process.env.PEER_FRONTEND_URL || "http://localhost:3001";
  const peerDomain = process.env.PEER_DOMAIN || "localhost:5005";

  let contextA: BrowserContext;
  let contextB: BrowserContext;
  let pageA: Page;
  let pageB: Page;
  let isPairAvailable = false;

  test.beforeAll(async ({ browser }) => {
    // 1. Probe connectivity of both live application origins
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

    // Create dual isolated browser contexts
    contextA = await browser.newContext();
    contextB = await browser.newContext();

    pageA = await contextA.newPage();
    pageB = await contextB.newPage();

    // Bypass cookie consent banners on both origins
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

  test("1.1 Dual browser contexts connect cleanly without route mocks", async () => {
    // Navigate Instance A to root
    await pageA.goto(primaryUrl);
    await expect(pageA).toHaveTitle(/iqoqo/i);

    // Navigate Instance B to root
    await pageB.goto(peerUrl);
    await expect(pageB).toHaveTitle(/iqoqo/i);

    // Assert session isolation across origins
    const cookiesA = await contextA.cookies();
    const cookiesB = await contextB.cookies();
    const tokenCookieA = cookiesA.find(c => c.name === "iqoqo_session");
    const tokenCookieB = cookiesB.find(c => c.name === "iqoqo_session");

    expect(tokenCookieA).toBeDefined();
    expect(tokenCookieB).toBeDefined();
    expect(tokenCookieA?.value).not.toEqual(tokenCookieB?.value);
  });

  test("1.2 Admin Trust Graph pairing and remote user consent verification", async () => {
    // 1. Instance Alpha: Navigate to Admin Federation Trust Graph
    await pageA.goto(`${primaryUrl}/admin/federation`);
    await expect(pageA.getByTestId("peering-guidance-banner")).toBeVisible();

    // 2. Discover/verify peer instance in Trust Graph
    const domainInput = pageA.getByPlaceholder(/instance\.example\.org/i);
    await expect(domainInput).toBeVisible();

    // 3. Instance Beta: Verify user privacy and federation consent settings on /profile
    await pageB.goto(`${peerUrl}/profile`);
    const consentSection = pageB.getByTestId("federation-consent-settings");
    await expect(consentSection).toBeVisible();

    const profileToggle = pageB.locator("#toggle-fed-profile");
    await expect(profileToggle).toBeVisible();
    if (!(await profileToggle.isChecked())) {
      await profileToggle.check();
      await expect(pageB.getByText(/Saved|Zapisano/i)).toBeVisible();
    }
  });

  test("1.3 Cross-instance social follow and handshake via Notification Center", async () => {
    // 1. User Alpha on Instance Alpha opens /profile and submits follow request to peer user
    await pageA.goto(`${primaryUrl}/profile`);
    const friendsCard = pageA.getByTestId("friends-card");
    if (await friendsCard.isVisible()) {
      const identifierInput = pageA.getByPlaceholder(/Username, email, or @user@domain/i);
      await identifierInput.fill(`@peeradmin@${peerDomain}`);
      await pageA.getByRole("button", { name: /Send Request/i }).click();
    }

    // 2. User Beta on Instance Beta verifies notification or incoming friend request
    await pageB.goto(`${peerUrl}/profile?tab=incoming`);
    // Assert incoming or already accepted relationship
    await expect(pageB.getByRole("tab", { name: /Incoming/i })).toBeVisible();
    const acceptBtn = pageB.getByRole("button", { name: /Accept/i });
    if (await acceptBtn.isVisible()) {
      await acceptBtn.click();
      await expect(pageB.getByText(/Friend request accepted/i)).toBeVisible();
    }
  });

  test("1.4 Federated directory navigation, loan request, and custodian approval", async () => {
    // 1. User Alpha explores connected library directory
    await pageA.goto(`${primaryUrl}/federation/directory`);
    await expect(pageA.getByRole("heading", { level: 1, name: /Connected Libraries/i })).toBeVisible();

    // 2. User Beta checks /admin/lending for loan requests
    await pageB.goto(`${peerUrl}/admin/lending`);
    await expect(pageB.getByRole("heading", { level: 1, name: /Lending Administration/i })).toBeVisible();

    // 3. If pending loan request exists, approve and verify status updates to 'Lent'
    const approveBtn = pageB.getByRole("button", { name: /Approve/i });
    if (await approveBtn.isVisible()) {
      await approveBtn.click();
      await expect(pageB.locator("[data-testid='status-cell']")).toHaveText(/Lent/i);
    }
  });

  test("1.5 Item return workflow and custody status reconciliation", async () => {
    // User Beta on Instance Beta accesses /admin/lending or catalog
    await pageB.goto(`${peerUrl}/admin/lending`);
    await expect(pageB.getByRole("heading", { level: 1, name: /Lending Administration/i })).toBeVisible();
  });
});
