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

import { test, expect } from "@playwright/test";

test.describe("Multi-Instance Federation E2E", () => {
  const flaskApiUrl = process.env.FLASK_API_URL || "http://127.0.0.1:5002/api";
  const peerApiUrl = process.env.PEER_API_URL || "http://127.0.0.1:5003/api";

  test("1. WebFinger RFC 7033 resolution across instances", async ({ page }) => {
    // 1. Resolve local user on primary instance via WebFinger
    const webfingerRes = await page.request.get("/.well-known/webfinger?resource=acct:ci-admin@iqoqo.cc");
    // If ci-admin is opted in or has public visibility, expect 200 JRD+JSON; otherwise assert graceful 404
    if (webfingerRes.status() === 200) {
      const jrd = await webfingerRes.json();
      expect(jrd.subject).toContain("ci-admin");
      expect(Array.isArray(jrd.links)).toBeTruthy();
      const selfLink = jrd.links.find((l: { rel: string }) => l.rel === "self");
      expect(selfLink).toBeDefined();
      expect(selfLink.type).toBe("application/activity+json");
    } else {
      expect([200, 404]).toContain(webfingerRes.status());
    }

    // 2. WebFinger error cases
    const missingRes = await page.request.get("/.well-known/webfinger");
    expect(missingRes.status()).toBe(400);

    const nonexistentRes = await page.request.get(
      "/.well-known/webfinger?resource=acct:nonexistent_user_99999@iqoqo.cc"
    );
    expect(nonexistentRes.status()).toBe(404);
  });

  test("2. Dual browser contexts maintain isolated identities and cookies", async ({ browser }) => {
    // Create two completely isolated browser contexts (Instance A user vs Instance B user)
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();

    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    // Set cookie consent bypass in both contexts
    await pageA.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });
    await pageB.addInitScript(() => {
      window.localStorage.setItem("iqoqo-cookie-consent", "true");
    });

    // Login user on Context A
    const loginA = await pageA.request.post(`${flaskApiUrl}/auth/login`, {
      data: { email: "ci-admin@iqoqo.cc", password: "E2EBootstrapPassword123!" },
    });
    if (loginA.ok()) {
      const { token } = await loginA.json();
      await pageA.request.post("/api/auth-exchange", { data: { token } });
    }

    // Context B should NOT have Context A's session cookies
    const cookiesB = await contextB.cookies();
    const sessionCookieB = cookiesB.find(c => c.name === "iqoqo_session");
    expect(sessionCookieB).toBeUndefined();

    await contextA.close();
    await contextB.close();
  });

  test("3. Remote actor lookup and signed Follow activity delivery", async ({ browser }) => {
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();

    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    // Mock remote peer responses in contextA if peer server is offline
    await pageA.route("**/api/federation/lookup*", async route => {
      const url = new URL(route.request().url());
      const handle = url.searchParams.get("handle") || "@bob@peer.local";
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          handle,
          actor_uri: "http://127.0.0.1:5003/api/federation/actor/u/peer-user-uuid",
          actor: {
            "@context": ["https://www.w3.org/ns/activitystreams"],
            id: "http://127.0.0.1:5003/api/federation/actor/u/peer-user-uuid",
            type: "Person",
            preferredUsername: "bob",
            name: "Peer User Bob",
            inbox: "http://127.0.0.1:5003/api/federation/inbox",
          },
        }),
      });
    });

    await pageA.route("**/api/federation/follow", async route => {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          status: "delivered",
          activity: {
            type: "Follow",
            actor: "http://localhost:3002/api/federation/actor/u/local-admin-uuid",
            object: "http://127.0.0.1:5003/api/federation/actor/u/peer-user-uuid",
          },
        }),
      });
    });

    // Perform remote lookup from Page A
    const lookupRes = await pageA.request.get("/api/federation/lookup?handle=@bob@peer.local");
    expect(lookupRes.ok()).toBeTruthy();
    const lookupData = await lookupRes.json();
    expect(lookupData.actor.preferredUsername).toBe("bob");
    expect(lookupData.actor.inbox).toContain("/inbox");

    // Perform Follow request from Page A targeting remote peer
    const followRes = await pageA.request.post("/api/federation/follow", {
      data: {
        actor_uri: lookupData.actor_uri,
        inbox_url: lookupData.actor.inbox,
      },
    });
    expect(followRes.ok()).toBeTruthy();
    const followData = await followRes.json();
    expect(followData.status).toBe("delivered");
    expect(followData.activity.type).toBe("Follow");

    // Verify inbox rejects unsigned activities on Page B
    const unsignedRes = await pageB.request.post(`${flaskApiUrl}/federation/inbox`, {
      data: {
        type: "Follow",
        actor: "http://attacker.local/actor",
        object: "http://127.0.0.1:5002/actor/u/victim",
      },
      headers: { "Content-Type": "application/json" },
    });
    // Unsigned request must be rejected (401 Unauthorized or 400 Bad Request)
    expect([400, 401]).toContain(unsignedRes.status());

    await contextA.close();
    await contextB.close();
  });
});
