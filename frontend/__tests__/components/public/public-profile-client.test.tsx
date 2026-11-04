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

import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PublicProfileClient } from "@/components/public/public-profile-client";
import * as routeParams from "@/lib/capacitor/route-params";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar">Navbar</nav>,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer">Footer</footer>,
}));

vi.mock("@/components/ui/share-button", () => ({
  ShareButton: () => <button>Share</button>,
}));

vi.mock("@/components/public/check-inventory", () => ({
  CheckInventory: ({ username }: { username: string }) => (
    <div data-testid="check-inventory">Inventory for {username}</div>
  ),
}));

vi.mock("@/components/collection/collection-grid", () => ({
  CollectionGrid: ({ items }: { items: unknown[] }) => (
    <div data-testid="collection-grid">Items count: {items.length}</div>
  ),
}));

vi.mock("@/components/public/public-profile-pager", () => ({
  PublicProfilePager: () => <div data-testid="pager">Pager</div>,
}));

describe("PublicProfileClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders initial SSR profile data directly", () => {
    const mockData = {
      user: {
        username: "jane_collector",
        display_name: "Jane Doe",
        bio: "Collector of rare books",
        public_item_count: 42,
      },
      items: [{ id: 1, title: "Book One" } as any],
      meta: { pages: 2, total: 42 },
      currentPage: 1,
    };

    render(<PublicProfileClient initialData={mockData} initialUsername="jane_collector" />);

    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("@jane_collector")).toBeInTheDocument();
    expect(screen.getByText("Collector of rare books")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByTestId("collection-grid")).toHaveTextContent("Items count: 1");
  });

  it("client-hydrates and fetches profile and items on native placeholder", async () => {
    vi.spyOn(routeParams, "useResolvedRouteParam").mockReturnValue("mark_reader");

    const mockUserRes = {
      success: true,
      data: {
        username: "mark_reader",
        display_name: "Mark Twain",
        bio: "Stories from the river",
        public_item_count: 5,
      },
    };

    const mockItemsRes = {
      data: {
        items: [
          { id: 10, title: "Tom Sawyer" },
          { id: 11, title: "Huckleberry Finn" },
        ],
      },
      meta: { pages: 1, total: 2 },
    };

    vi.spyOn(global, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockUserRes,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockItemsRes,
      } as Response);

    render(<PublicProfileClient initialData={null} initialUsername="_placeholder" />);

    await waitFor(() => {
      expect(screen.getByText("Mark Twain")).toBeInTheDocument();
    });

    expect(screen.getByText("@mark_reader")).toBeInTheDocument();
    expect(screen.getByTestId("collection-grid")).toHaveTextContent("Items count: 2");
  });

  it("renders user not found when user API returns 404", async () => {
    vi.spyOn(routeParams, "useResolvedRouteParam").mockReturnValue("ghost_user");

    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: false,
      status: 404,
    } as Response);

    render(<PublicProfileClient initialData={null} initialUsername="_placeholder" />);

    await waitFor(() => {
      expect(screen.getByText("User Not Found")).toBeInTheDocument();
    });
  });
});
