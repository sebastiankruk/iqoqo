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
/**
 * Unit tests for frontend/lib/capacitor/navigation.ts
 *
 * Verifies the deep-link URL parsing logic and back-button handler wiring
 * without requiring a real Capacitor runtime.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

// ─── Mocks ───────────────────────────────────────────────────────────────────

let mockIsNative = true;

const appListeners: Record<string, (data: unknown) => void> = {};
const mockExitApp = vi.fn();

vi.mock("@capacitor/app", () => ({
  App: {
    addListener: vi.fn((event: string, cb: (data: unknown) => void) => {
      appListeners[event] = cb;
    }),
    exitApp: mockExitApp,
    getLaunchUrl: vi.fn().mockResolvedValue({ url: undefined }),
  },
}));

vi.mock("@/lib/capacitor/platform", () => ({
  isNativeApp: () => mockIsNative,
}));

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Simulate firing a Capacitor App event.
 * @param event - Event name to fire.
 * @param data - Event payload.
 */
function fireEvent(event: string, data: unknown) {
  appListeners[event]?.(data);
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("registerBackButtonHandler", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    mockIsNative = true;
    Object.keys(appListeners).forEach(k => delete appListeners[k]);
  });

  it("navigates back when canGoBack is true", async () => {
    const { registerBackButtonHandler } = await import("@/lib/capacitor/navigation");
    const router = { back: vi.fn() };
    registerBackButtonHandler(router);
    fireEvent("backButton", { canGoBack: true });
    expect(router.back).toHaveBeenCalledOnce();
  });

  it("exits the app when canGoBack is false", async () => {
    const { registerBackButtonHandler } = await import("@/lib/capacitor/navigation");
    const router = { back: vi.fn() };
    registerBackButtonHandler(router);
    fireEvent("backButton", { canGoBack: false });
    expect(router.back).not.toHaveBeenCalled();
    expect(mockExitApp).toHaveBeenCalledOnce();
  });

  it("does not register on web", async () => {
    mockIsNative = false;
    const { App } = await import("@capacitor/app");
    const { registerBackButtonHandler } = await import("@/lib/capacitor/navigation");
    const router = { back: vi.fn() };
    registerBackButtonHandler(router);
    expect(App.addListener).not.toHaveBeenCalled();
  });
});

describe("registerDeepLinkHandler", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    mockIsNative = true;
    Object.keys(appListeners).forEach(k => delete appListeners[k]);
  });

  it("pushes /auth-exchange?token=... when an iqoqo:// deep link arrives", async () => {
    const { registerDeepLinkHandler } = await import("@/lib/capacitor/navigation");
    const router = { push: vi.fn() };
    registerDeepLinkHandler(router);
    fireEvent("appUrlOpen", { url: "iqoqo://auth-exchange?token=my-jwt" });
    expect(router.push).toHaveBeenCalledWith("/auth-exchange?token=my-jwt");
  });

  it("ignores malformed URLs without throwing", async () => {
    const { registerDeepLinkHandler } = await import("@/lib/capacitor/navigation");
    const router = { push: vi.fn() };
    registerDeepLinkHandler(router);
    expect(() => fireEvent("appUrlOpen", { url: "not-a-url" })).not.toThrow();
    expect(router.push).not.toHaveBeenCalled();
  });

  it("does not register on web", async () => {
    mockIsNative = false;
    const { App } = await import("@capacitor/app");
    const { registerDeepLinkHandler } = await import("@/lib/capacitor/navigation");
    const router = { push: vi.fn() };
    registerDeepLinkHandler(router);
    expect(App.addListener).not.toHaveBeenCalled();
  });
});
