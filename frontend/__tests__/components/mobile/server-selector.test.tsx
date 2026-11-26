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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ServerSelector } from "@/components/mobile/server-selector";
import * as storage from "@/lib/capacitor/storage";
import * as offlineCache from "@/lib/capacitor/offline-cache";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, string>) =>
    params ? `${key}:${JSON.stringify(params)}` : key,
}));

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

describe("ServerSelector Multi-Server Switching (C156)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  const renderWithQuery = (ui: React.ReactElement) => {
    const qc = new QueryClient();
    return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
  };

  it("renders saved servers, switches active server without wiping other tokens, and removes servers", async () => {
    const srvA = await storage.saveServerProfile({ url: "https://a.iqoqo.cc", name: "Server A" }, true);
    await storage.setAuthToken("tok-a");
    await offlineCache.saveCollectionSnapshot([{ id: 1, title: "Book A" } as never]);

    const srvB = await storage.saveServerProfile({ url: "https://b.iqoqo.cc", name: "Server B" }, true);
    await storage.setAuthToken("tok-b");
    await offlineCache.saveCollectionSnapshot([{ id: 2, title: "Book B" } as never]);

    const onConnected = vi.fn();
    renderWithQuery(<ServerSelector onConnected={onConnected} />);

    await waitFor(() => {
      expect(screen.getByTestId("saved-servers-list")).toBeInTheDocument();
      expect(screen.getByText("Server A")).toBeInTheDocument();
      expect(screen.getByText("Server B")).toBeInTheDocument();
    });

    // Switch to Server A
    const switchButtons = screen.getAllByText("switchToServer");
    expect(switchButtons).toHaveLength(1);
    fireEvent.click(switchButtons[0]);

    await waitFor(() => {
      expect(onConnected).toHaveBeenCalledWith("https://a.iqoqo.cc", "Server A");
    });

    // Both tokens and offline caches remain isolated and intact
    expect(await storage.getAuthToken(srvA.id)).toBe("tok-a");
    expect(await storage.getAuthToken(srvB.id)).toBe("tok-b");
    expect((await offlineCache.getCachedCollectionSnapshot(srvA.id))?.items[0].title).toBe("Book A");
    expect((await offlineCache.getCachedCollectionSnapshot(srvB.id))?.items[0].title).toBe("Book B");

    // Remove Server B
    const removeButtons = screen.getAllByLabelText("removeServer");
    fireEvent.click(removeButtons[1]);

    await waitFor(() => {
      expect(screen.queryByText("Server B")).not.toBeInTheDocument();
    });
    expect((await offlineCache.getCachedCollectionSnapshot(srvA.id))?.items[0].title).toBe("Book A");
    expect(await offlineCache.getCachedCollectionSnapshot(srvB.id)).toBeNull();
  });
});
