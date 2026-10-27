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

import { test, expect } from "@playwright/test";
import packageJson from "../../package.json" assert { type: "json" };

test.describe("Federated Friend Request Direction and Cancellation (C87f)", () => {
  test("outbound federated follow appears in Outgoing tab with Cancel and not in Incoming tab", async ({ page }) => {
    // 0. Ensure user has authenticated session cookie so Next.js proxy doesn't redirect to /login
    await page.context().addCookies([{ name: "iqoqo_session", value: "mock-session", domain: "localhost", path: "/" }]);

    // 1. Mock system config & profile endpoints
    await page.route("**/api/config**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { federation_enabled: true, version: packageJson.version },
        }),
      });
    });

    await page.route(
      url => url.pathname === "/api/profile/" || url.pathname === "/api/profile",
      async route => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              id: "11111111-1111-1111-1111-111111111111",
              email: "bob@local.instance",
              public_username: "bob",
              display_name: "Bob Local",
              bio: "",
              avatar_url: "",
              visibility: "private",
              default_item_visibility: "private",
              consents: {},
            },
          }),
        });
      }
    );

    await page.route("**/api/profile/consents**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { federated_profile: true, discoverable: true },
        }),
      });
    });

    await page.route("**/api/profile/pending-deletion**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { is_pending_deletion: false },
        }),
      });
    });

    await page.route("**/api/auth/2fa/status**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { totp_enabled: false },
        }),
      });
    });

    await page.route("**/api/auth/tokens**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [],
        }),
      });
    });

    await page.route("**/api/escalations/mine**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [],
        }),
      });
    });

    await page.route("**/api/v1/notifications**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [],
        }),
      });
    });

    await page.route("**/api/auth/providers**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ google: false }),
      });
    });

    // 2. Track friends state across requests
    let outgoingList: any[] = [];
    const incomingList: any[] = [];
    const acceptedList: any[] = [];

    await page.route("**/api/profile/friends/request", async route => {
      const body = JSON.parse(route.request().postData() || "{}");
      const identifier = body.identifier || "@alice@peer.iqoqo.cc";
      outgoingList = [
        {
          friendship_id: "fed:101",
          user_id: "remote-alice-actor-id",
          username: identifier.replace(/^@/, ""),
          display_name: "Alice Remote",
          status: "pending",
          is_federated: true,
          actor_uri: "https://peer.iqoqo.cc/api/federation/actor/u/alice",
          created_at: new Date().toISOString(),
        },
      ];
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: outgoingList[0],
        }),
      });
    });

    await page.route("**/api/profile/friends/fed%3A101", async route => {
      if (route.request().method() === "DELETE") {
        outgoingList = [];
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      } else {
        await route.fallback();
      }
    });

    await page.route("**/api/profile/friends", async route => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              accepted: acceptedList,
              incoming: incomingList,
              outgoing: outgoingList,
            },
          }),
        });
      } else {
        await route.fallback();
      }
    });

    // 3. Navigate to profile page
    await page.goto("/profile");

    // 4. Verify federated profile consent hint is rendered
    await expect(
      page.getByText(/For federated users \(@user@domain\), the remote user must have enabled 'Federated Profile'/i)
    ).toBeVisible();

    // 5. Send friend request to remote federated handle
    const handleInput = page.getByPlaceholder(/Username, email, or @user@domain handle/i);
    await handleInput.fill("@alice@peer.iqoqo.cc");

    const sendButton = page.getByRole("button", { name: /Send Request/i });
    await sendButton.click();

    // 6. Check Incoming tab -> must be empty
    const incomingTab = page.getByRole("button", { name: /Incoming \(/i });
    await incomingTab.click();
    await expect(page.getByText(/No pending incoming requests/i)).toBeVisible();
    await expect(page.getByText("Alice Remote")).not.toBeVisible();

    // 7. Check Outgoing tab -> must show Alice Remote with Fediverse badge and Cancel action
    const outgoingTab = page.getByRole("button", { name: /Outgoing \(/i });
    await outgoingTab.click();
    await expect(page.getByText("Alice Remote")).toBeVisible();
    await expect(page.getByText("Fediverse")).toBeVisible();
    await expect(page.getByText("Pending")).toBeVisible();

    const cancelButton = page.getByRole("button", { name: /Cancel/i });
    await expect(cancelButton).toBeVisible();

    // 8. Cancel request
    await cancelButton.click();
    await expect(page.getByText(/No outgoing requests/i)).toBeVisible();
  });
});
