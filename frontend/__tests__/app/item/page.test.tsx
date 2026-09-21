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
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ItemPageClient } from "@/components/item/item-page-client";
import * as hooks from "@/lib/api/hooks";
import type { Item } from "@/types/frbr";

// Mock Next.js navigation
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
    replace: vi.fn(),
  })),
  usePathname: vi.fn().mockReturnValue("/item/1"),
}));

// Mock Navbar
vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <div data-testid="navbar">Navbar</div>,
}));

// Mock item sub-components to isolate page-level testing
vi.mock("@/components/item/hero-banner", () => ({
  HeroBanner: ({ title }: { title?: string }) => <div data-testid="hero-banner">{title ?? "Hero Banner"}</div>,
}));

vi.mock("@/components/item/item-sidebar", () => ({
  ItemSidebar: ({ item }: { item: Item }) => <div data-testid="item-sidebar">{item.work?.title ?? item.title}</div>,
}));

vi.mock("@/components/item/item-header", () => ({
  ItemHeader: ({ item }: { item: Item }) => <div data-testid="item-header">{item.work?.title ?? item.title}</div>,
}));

vi.mock("@/components/item/item-actions", () => ({
  ItemActions: ({ item }: { item: Item }) => (
    <div data-testid="item-actions">
      <button data-testid="edit-btn">Edit</button>
      <button data-testid="delete-btn">Delete</button>
      <button data-testid="export-btn">Export</button>
    </div>
  ),
}));

vi.mock("@/components/item/item-tabs", () => ({
  ItemTabs: ({ item }: { item: Item }) => <div data-testid="item-tabs">Tabs for {item.work?.title ?? item.title}</div>,
}));

vi.mock("@/lib/api/hooks", () => ({
  useItem: vi.fn(),
  useManifestationWithPolling: vi.fn(({ item }: { item: Item }) => ({ item })),
}));

vi.mock("@/lib/utils", () => ({
  getCoverUrl: vi.fn(() => null),
  getCoverTimestamp: vi.fn(() => null),
}));

const mockItem: Item = {
  id: 1,
  manifestation_id: 10,
  title: "Test Book",
  isbn: "9780451524935",
  cover_url: null,
  content_type: "book",
  status: "read",
  is_hidden: false,
  meta: {},
  manifestation_meta: {},
  work: {
    id: 100,
    title: "1984",
    authors: ["George Orwell"],
  },
  expression: {
    language: "en",
    content_type: "book",
    kind: "text",
  },
} as unknown as Item;

describe("ItemPageClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state initially", () => {
    vi.mocked(hooks.useItem).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof hooks.useItem>);

    render(<ItemPageClient itemId={1} />);

    // Loading skeleton should be visible
    expect(screen.getByTestId("navbar")).toBeInTheDocument();
  });

  it("renders item details when data is loaded", () => {
    vi.mocked(hooks.useItem).mockReturnValue({
      data: mockItem,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof hooks.useItem>);

    render(<ItemPageClient itemId={1} />);

    // Hero banner should show the work title
    expect(screen.getByTestId("hero-banner")).toHaveTextContent("1984");

    // Sidebar should be visible
    expect(screen.getByTestId("item-sidebar")).toBeInTheDocument();

    // Header should be visible
    expect(screen.getByTestId("item-header")).toBeInTheDocument();

    // Tabs should be visible
    expect(screen.getByTestId("item-tabs")).toBeInTheDocument();

    // Actions should be visible
    expect(screen.getByTestId("item-actions")).toBeInTheDocument();
  });

  it("displays error state when item is not found", () => {
    vi.mocked(hooks.useItem).mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof hooks.useItem>);

    render(<ItemPageClient itemId={999} />);

    expect(screen.getByText("Item not found.")).toBeInTheDocument();
    expect(screen.getByText("Back to collection")).toBeInTheDocument();
  });

  it("displays error state when useItem returns no data", () => {
    vi.mocked(hooks.useItem).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof hooks.useItem>);

    render(<ItemPageClient itemId={999} />);

    expect(screen.getByText("Item not found.")).toBeInTheDocument();
  });

  it("renders item actions (edit, delete, export)", () => {
    vi.mocked(hooks.useItem).mockReturnValue({
      data: mockItem,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof hooks.useItem>);

    render(<ItemPageClient itemId={1} />);

    expect(screen.getByTestId("edit-btn")).toBeInTheDocument();
    expect(screen.getByTestId("delete-btn")).toBeInTheDocument();
    expect(screen.getByTestId("export-btn")).toBeInTheDocument();
  });

  it("renders back to collection button", () => {
    vi.mocked(hooks.useItem).mockReturnValue({
      data: mockItem,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof hooks.useItem>);

    render(<ItemPageClient itemId={1} />);

    // Footer should have a back button
    const backButtons = screen.getAllByText("Back to collection");
    expect(backButtons.length).toBeGreaterThan(0);
  });

  it("renders iqoqo branding in footer", () => {
    vi.mocked(hooks.useItem).mockReturnValue({
      data: mockItem,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof hooks.useItem>);

    render(<ItemPageClient itemId={1} />);

    // Footer contains "iqoqo" text
    expect(screen.getByText(/iqoqo/)).toBeInTheDocument();
  });
});
