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
import userEvent from "@testing-library/user-event";
import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ServerSelector, ServerSelectorModal } from "@/components/mobile/server-selector";
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

describe("ServerSelector Connection Validation & Multi-Server Switching (C156)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  const renderWithQuery = (ui: React.ReactElement) => {
    const qc = new QueryClient();
    return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
  };

  it("renders URL input and verify button initially", () => {
    renderWithQuery(<ServerSelector />);
    expect(screen.getByLabelText("serverUrlLabel")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "verifyConnection" })).toBeDisabled();
  });

  it("validates invalid URLs without calling fetch", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    renderWithQuery(<ServerSelector />);

    await user.type(screen.getByLabelText("serverUrlLabel"), "http://invalid host name");
    await user.click(screen.getByRole("button", { name: "verifyConnection" }));

    expect(screen.getByText("invalidUrl")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("probes /api/health and /api/config and calls onConnected on success", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: "ok" }), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ data: { instance_name: "Home Archive", version: "1.2.0" } }), { status: 200 })
      );

    const onConnected = vi.fn();
    renderWithQuery(<ServerSelector onConnected={onConnected} />);

    await user.type(screen.getByLabelText("serverUrlLabel"), "library.example.com");
    await user.click(screen.getByRole("button", { name: "verifyConnection" }));

    await waitFor(() => {
      expect(onConnected).toHaveBeenCalledWith("https://library.example.com", "Home Archive");
    });
    expect(fetchSpy).toHaveBeenNthCalledWith(1, "https://library.example.com/api/health", expect.any(Object));
    expect(fetchSpy).toHaveBeenNthCalledWith(2, "https://library.example.com/api/config", expect.any(Object));
    fetchSpy.mockRestore();
  });

  it("displays connectionFailed when /api/health returns non-OK status", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response("Service Unavailable", { status: 503 }));

    renderWithQuery(<ServerSelector />);
    await user.type(screen.getByLabelText("serverUrlLabel"), "https://down.example.com");
    await user.click(screen.getByRole("button", { name: "verifyConnection" }));

    await waitFor(() => {
      expect(screen.getByText("connectionFailed")).toBeInTheDocument();
    });
    fetchSpy.mockRestore();
  });

  it("renders saved servers, switches active server, renames inline, and removes active server safely", async () => {
    const user = userEvent.setup();
    const srvA = await storage.saveServerProfile({ url: "https://a.iqoqo.cc", name: "Server A" }, true);
    await storage.setAuthToken("tok-a");
    await offlineCache.saveCollectionSnapshot([{ id: 1, title: "Book A" } as never]);

    const srvB = await storage.saveServerProfile({ url: "https://b.iqoqo.cc", name: "Server B" }, true);
    await storage.setAuthToken("tok-b");
    await offlineCache.saveCollectionSnapshot([{ id: 2, title: "Book B" } as never]);

    const onConnected = vi.fn();
    renderWithQuery(<ServerSelector onConnected={onConnected} />);

    await waitFor(() => {
      expect(screen.getByText("Server A")).toBeInTheDocument();
      expect(screen.getByText("Server B")).toBeInTheDocument();
    });

    // Switch to Server A without wiping B's token/cache
    await user.click(screen.getByRole("button", { name: "switchToServer" }));

    await waitFor(() => {
      expect(onConnected).toHaveBeenCalledWith("https://a.iqoqo.cc", "Server A");
    });

    expect(await storage.getAuthToken(srvA.id)).toBe("tok-a");
    expect(await storage.getAuthToken(srvB.id)).toBe("tok-b");
    expect((await offlineCache.getCachedCollectionSnapshot(srvA.id))?.items[0].title).toBe("Book A");
    expect((await offlineCache.getCachedCollectionSnapshot(srvB.id))?.items[0].title).toBe("Book B");

    // Rename Server B inline
    const rowB = screen.getByTestId(`saved-server-${srvB.id}`);
    await user.click(within(rowB).getByRole("button", { name: "renameServer" }));
    const renameInput = within(rowB).getByLabelText("serverNameLabel");
    await user.clear(renameInput);
    await user.type(renameInput, "Staging B");
    await user.click(within(rowB).getByRole("button", { name: "saveName" }));

    await waitFor(() => {
      expect(screen.getByText("Staging B")).toBeInTheDocument();
    });

    // Remove currently active Server A -> cleanly promotes Staging B
    const rowA = screen.getByTestId(`saved-server-${srvA.id}`);
    await user.click(within(rowA).getByRole("button", { name: "removeServer" }));

    await waitFor(() => {
      expect(screen.queryByText("Server A")).not.toBeInTheDocument();
    });
    expect(await offlineCache.getCachedCollectionSnapshot(srvA.id)).toBeNull();
    expect((await offlineCache.getCachedCollectionSnapshot(srvB.id))?.items[0].title).toBe("Book B");
    expect(await storage.getActiveServerId()).toBe(srvB.id);
  });

  it("renders ServerSelectorModal when open and cancels cleanly", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithQuery(<ServerSelectorModal isOpen={true} onClose={onClose} />);

    expect(screen.getByText("serverSelectorTitle")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "cancel" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
