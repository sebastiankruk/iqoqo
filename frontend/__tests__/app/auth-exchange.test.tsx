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
// frontend/__tests__/app/auth-exchange.test.tsx

import React from "react";
import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AuthExchangePage from "@/app/auth-exchange/page";
import * as platform from "@/lib/capacitor/platform";
import * as storage from "@/lib/capacitor/storage";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const mockReplace = vi.fn();
let mockToken: string | null = "test-token-123";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
  }),
  useSearchParams: () => ({
    get: (key: string) => (key === "token" ? mockToken : null),
  }),
}));

const mockClear = vi.fn();
vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({
    clear: mockClear,
  }),
  QueryClient: class {
    clear = mockClear;
  },
  QueryClientProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/lib/capacitor/platform", () => ({
  isNativeApp: vi.fn(),
}));

vi.mock("@/lib/capacitor/storage", () => ({
  setAuthToken: vi.fn(),
}));

const testQueryClient = new QueryClient();

describe("AuthExchangePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockToken = "test-token-123";
    global.fetch = vi.fn().mockResolvedValue({
      redirected: false,
      url: "http://localhost:3000/",
    });
  });

  it("redirects to login when token is missing", async () => {
    mockToken = null;
    render(
      <QueryClientProvider client={testQueryClient}>
        <AuthExchangePage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login");
    });
  });

  it("handles native platform exchange cleanly", async () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    const setAuthTokenSpy = vi.spyOn(storage, "setAuthToken").mockResolvedValue(undefined);

    render(
      <QueryClientProvider client={testQueryClient}>
        <AuthExchangePage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(setAuthTokenSpy).toHaveBeenCalledWith("test-token-123");
      expect(mockClear).toHaveBeenCalled();
      expect(mockReplace).toHaveBeenCalledWith("/");
    });
  });

  it("handles web platform exchange cleanly", async () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(false);
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue({
      redirected: true,
      url: "http://localhost:3000/profile",
    } as Response);

    render(
      <QueryClientProvider client={testQueryClient}>
        <AuthExchangePage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith("/api/auth-exchange?token=test-token-123");
      expect(mockReplace).toHaveBeenCalledWith("/profile");
    });
  });
});
