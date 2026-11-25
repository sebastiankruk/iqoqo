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
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import enMessages from "@/messages/en.json";
import { ShareCollectionDialog } from "@/components/collection/share-collection-dialog";
import { apiClient } from "@/lib/api/client";

const mockCookies = vi.fn();

vi.mock("next/headers", () => ({
  cookies: () => mockCookies(),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, string>) => {
    const dict = enMessages.ShareCollection as Record<string, string>;
    let template = dict[key] ?? key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        template = template.replace(`{${k}}`, v);
      }
    }
    return template;
  },
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe("C129 ShareCollectionDialog & SSR cookie forwarding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("defaults to public_only without privacy warning and submits public_only", async () => {
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { success: true, data: { share_token: "tok-pub" } },
    });

    render(<ShareCollectionDialog activeFilters={[]} appliedQuery="" />);
    fireEvent.click(screen.getByRole("button", { name: /share view/i }));

    const publicRadio = screen.getByRole("radio", { name: /public only/i }) as HTMLInputElement;
    expect(publicRadio.checked).toBe(true);
    expect(screen.queryByRole("alert")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /generate link/i }));
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/sharing/",
        expect.objectContaining({
          visibility_scope: "public_only",
          filters: expect.objectContaining({ visibility_scope: "public_only" }),
        })
      );
    });
  });

  it("shows warning and transmits visibility_scope='all' when All items is chosen", async () => {
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { success: true, data: { share_token: "tok-all" } },
    });

    render(<ShareCollectionDialog activeFilters={[{ type: "status", value: "read" }]} appliedQuery="" />);
    fireEvent.click(screen.getByRole("button", { name: /share view/i }));

    fireEvent.click(screen.getByRole("radio", { name: /all items/i }));
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toMatch(/AI assistants/i);
    expect(alert.textContent).toMatch(/private/i);

    fireEvent.click(screen.getByRole("button", { name: /generate link/i }));
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/sharing/",
        expect.objectContaining({
          visibility_scope: "all",
          filters: expect.objectContaining({
            visibility_scope: "all",
            status: "read",
          }),
        })
      );
    });
  });

  it("forwards Cookie header and disables cache on SSR when session cookie is present", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => ({
        success: true,
        data: { author: "alice", collection_name: "Sci-Fi", items: [] },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    mockCookies.mockResolvedValue({ toString: () => "session=abc123" });

    const { getSharedCollection } = await import("@/lib/share-server");
    const result = await getSharedCollection("tok-friend");
    expect(result.kind).toBe("success");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/public/share/tok-friend"),
      expect.objectContaining({
        headers: { Cookie: "session=abc123" },
        cache: "no-store",
      })
    );

    fetchMock.mockClear();
    mockCookies.mockResolvedValue({ toString: () => "" });
    await getSharedCollection("tok-anon");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/public/share/tok-anon"),
      expect.objectContaining({
        cache: "no-store",
      })
    );

    vi.unstubAllGlobals();
  });

  it("serializes expression_kind and defaults name to Live Performances when live_performance is active", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, data: { share_token: "live-tok" } },
    });

    render(
      <ShareCollectionDialog activeFilters={[{ type: "expression_kind", value: "live_performance" }]} appliedQuery="" />
    );
    fireEvent.click(screen.getByRole("button", { name: /share/i }));

    const nameInput = screen.getByDisplayValue("Live Performances");
    expect(nameInput).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /create link|generate/i }));
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/sharing/",
        expect.objectContaining({
          name: "Live Performances",
          filters: expect.objectContaining({
            expression_kind: ["live_performance"],
          }),
        })
      );
    });
  });
});
