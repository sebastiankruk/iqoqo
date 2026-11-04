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
import { render, screen, waitFor } from "@testing-library/react";
import AuthExchangePage from "@/app/auth-exchange/page";
import * as platform from "@/lib/capacitor/platform";
import * as storage from "@/lib/capacitor/storage";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const mockReplace = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => mockSearchParams,
  usePathname: () => "/auth-exchange",
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
  useLocale: () => "en",
}));

vi.mock("next-themes", () => ({
  useTheme: () => ({ theme: "light", setTheme: vi.fn() }),
}));

describe("AuthExchangePage", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    mockSearchParams = new URLSearchParams();
    vi.spyOn(window.history, "replaceState").mockImplementation(() => {});
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AuthExchangePage />
      </QueryClientProvider>
    );

  it("persists token and routes to / directly on native mobile app", async () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    const spySetToken = vi.spyOn(storage, "setAuthToken").mockResolvedValue();
    mockSearchParams = new URLSearchParams("token=native-jwt-token-123");

    renderComponent();

    await waitFor(() => {
      expect(spySetToken).toHaveBeenCalledWith("native-jwt-token-123");
      expect(mockReplace).toHaveBeenCalledWith("/");
    });
  });

  it("renders mobile handoff card when mobile=1 in external mobile browser", async () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(false);
    mockSearchParams = new URLSearchParams("token=external-jwt-token-456&mobile=1");

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Open in iqoqo")).toBeDefined();
      expect(screen.getByText("Open iqoqo App")).toBeDefined();
    });

    const link = screen.getByRole("link", { name: /Open iqoqo App/i });
    expect(link.getAttribute("href")).toContain("iqoqo://auth-exchange?token=external-jwt-token-456");
  });

  it("exchanges code and redirects on web authorization flow", async () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(false);
    mockSearchParams = new URLSearchParams("code=exchange-code-789");
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ redirectUrl: "/collection" }),
    });

    renderComponent();

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/auth-exchange", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "exchange-code-789" }),
      });
      expect(mockReplace).toHaveBeenCalledWith("/collection");
    });
  });
});
