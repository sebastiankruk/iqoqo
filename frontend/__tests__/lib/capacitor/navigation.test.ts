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
import { describe, it, expect, vi, beforeEach } from "vitest";
import { App } from "@capacitor/app";
import { Browser } from "@capacitor/browser";
import {
  parseAppUrl,
  handleDeepLink,
  registerDeepLinkHandler,
  registerBackButtonHandler,
  openExternalUrl,
  type NavigationRouter,
} from "@/lib/capacitor/navigation";
import * as platform from "@/lib/capacitor/platform";
import * as storage from "@/lib/capacitor/storage";

vi.mock("@capacitor/browser", () => ({
  Browser: {
    open: vi.fn().mockResolvedValue(undefined),
    close: vi.fn().mockResolvedValue(undefined),
  },
}));

vi.mock("@capacitor/app", () => ({
  App: {
    getLaunchUrl: vi.fn(),
    addListener: vi.fn(),
    exitApp: vi.fn(),
  },
}));

describe("Capacitor Navigation & Deep Link Handler", () => {
  let mockRouter: NavigationRouter;

  beforeEach(() => {
    vi.clearAllMocks();
    mockRouter = {
      push: vi.fn(),
      replace: vi.fn(),
      back: vi.fn(),
    };
  });

  describe("parseAppUrl", () => {
    it("parses iqoqo://auth-exchange?token=XYZ query param", () => {
      const res = parseAppUrl("iqoqo://auth-exchange?token=my-jwt-token");
      expect(res.token).toBe("my-jwt-token");
      expect(res.path).toBe("/auth-exchange?token=my-jwt-token");
    });

    it("parses intent://auth-exchange?token=XYZ Android intent URL", () => {
      const res = parseAppUrl(
        "intent://auth-exchange?token=my-intent-token#Intent;scheme=iqoqo;package=cc.iqoqo.app;end"
      );
      expect(res.token).toBe("my-intent-token");
      expect(res.path).toContain("/auth-exchange?token=my-intent-token");
    });

    it("parses iqoqo://auth-exchange#token=XYZ hash param", () => {
      const res = parseAppUrl("iqoqo://auth-exchange#token=my-hash-token");
      expect(res.token).toBe("my-hash-token");
      expect(res.path).toBe("/auth-exchange");
    });

    it("parses deep link paths without token", () => {
      const res = parseAppUrl("iqoqo://item/42?view=details");
      expect(res.token).toBeNull();
      expect(res.path).toBe("/item/42?view=details");
    });

    it("falls back to root on invalid URLs", () => {
      const res = parseAppUrl("invalid-scheme://:foo");
      expect(res.path).toBe("/");
      expect(res.token).toBeNull();
    });
  });

  describe("handleDeepLink", () => {
    it("persists token, closes browser, and redirects to / on auth-exchange link", async () => {
      const spySetToken = vi.spyOn(storage, "setAuthToken").mockResolvedValue();
      const mockQueryClient = { clear: vi.fn() } as any;

      await handleDeepLink({ url: "iqoqo://auth-exchange?token=token-abc" }, mockRouter, mockQueryClient);

      expect(spySetToken).toHaveBeenCalledWith("token-abc");
      expect(mockQueryClient.clear).toHaveBeenCalled();
      expect(Browser.close).toHaveBeenCalled();
      expect(mockRouter.replace).toHaveBeenCalledWith("/");
    });

    it("navigates to deep linked resource path", async () => {
      await handleDeepLink({ url: "iqoqo://item/123" }, mockRouter);
      expect(mockRouter.push).toHaveBeenCalledWith("/item/123");
    });

    it("does not redirect when url is root localhost without token", async () => {
      await handleDeepLink({ url: "https://localhost/" }, mockRouter);
      expect(mockRouter.push).not.toHaveBeenCalled();
      expect(mockRouter.replace).not.toHaveBeenCalled();
    });
  });

  describe("registerDeepLinkHandler", () => {
    it("does nothing when running on web browser", () => {
      vi.spyOn(platform, "isNativeApp").mockReturnValue(false);
      const cleanup = registerDeepLinkHandler(mockRouter);
      expect(App.getLaunchUrl).not.toHaveBeenCalled();
      expect(App.addListener).not.toHaveBeenCalled();
      cleanup();
    });

    it("registers listeners when running on native platform", async () => {
      vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
      (App.getLaunchUrl as any).mockResolvedValue({ url: "iqoqo://item/999" });
      (App.addListener as any).mockResolvedValue({ remove: vi.fn() });

      const cleanup = registerDeepLinkHandler(mockRouter);
      expect(App.getLaunchUrl).toHaveBeenCalled();
      expect(App.addListener).toHaveBeenCalledWith("appUrlOpen", expect.any(Function));
      cleanup();
    });
  });

  describe("registerBackButtonHandler", () => {
    it("navigates back when canGoBack is true", async () => {
      vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
      let callback: any;
      (App.addListener as any).mockImplementation((event: string, cb: any) => {
        if (event === "backButton") callback = cb;
        return Promise.resolve({ remove: vi.fn() });
      });

      registerBackButtonHandler(mockRouter);
      expect(callback).toBeDefined();

      callback({ canGoBack: true });
      expect(mockRouter.back).toHaveBeenCalled();
      expect(App.exitApp).not.toHaveBeenCalled();
    });

    it("exits app when canGoBack is false", async () => {
      vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
      let callback: any;
      (App.addListener as any).mockImplementation((event: string, cb: any) => {
        if (event === "backButton") callback = cb;
        return Promise.resolve({ remove: vi.fn() });
      });

      registerBackButtonHandler(mockRouter);
      callback({ canGoBack: false });
      expect(App.exitApp).toHaveBeenCalled();
    });
  });

  describe("openExternalUrl", () => {
    it("opens URL via Browser.open on native platforms", async () => {
      vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
      await openExternalUrl("https://preview.iqoqo.cc/api/public/feed.xml");
      expect(Browser.open).toHaveBeenCalledWith({ url: "https://preview.iqoqo.cc/api/public/feed.xml" });
    });

    it("opens URL via window.open on web", async () => {
      vi.spyOn(platform, "isNativeApp").mockReturnValue(false);
      const windowOpenSpy = vi.spyOn(window, "open").mockImplementation(() => null);
      await openExternalUrl("https://preview.iqoqo.cc/api/public/feed.xml");
      expect(windowOpenSpy).toHaveBeenCalledWith(
        "https://preview.iqoqo.cc/api/public/feed.xml",
        "_blank",
        "noopener,noreferrer"
      );
    });
  });
});
