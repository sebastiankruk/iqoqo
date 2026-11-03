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
import { render, fireEvent, screen } from "@testing-library/react";
import { describe, it, expect, vi, type Mock, beforeEach } from "vitest";
import { Navbar } from "@/components/dashboard/navbar";
import { useProfile, useAppConfig } from "@/lib/api/hooks";
import { useMyEscalations } from "@/lib/api/escalations";
import { usePathname, useSearchParams, useRouter } from "next/navigation";

vi.mock("@/components/collection/manage-collections-modal", () => ({
  ManageCollectionsModal: () => null,
}));

vi.mock("@/components/dashboard/notification-center", () => ({
  NotificationCenter: () => null,
}));

vi.mock("@/components/language-toggle", () => ({
  LanguageToggle: () => null,
}));

vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: () => (key: string) => {
    const map: Record<string, string> = {
      home: "Home",
      scan: "Scan",
      collection: "Collection",
      search: "Search",
      signIn: "Sign In",
      profile: "Profile",
    };
    return map[key] || key;
  },
}));

// Mock the API hooks
vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
  useManifestations: vi.fn(),
  useRecentManifestations: vi.fn(() => ({ data: undefined, isLoading: false, isError: false })),
  useAppConfig: vi.fn(() => ({ data: { maintenance_mode: false }, isLoading: false })),
}));

// Mock escalation hooks used by the Navbar
vi.mock("@/lib/api/escalations", () => ({
  useMyEscalations: vi.fn(() => ({ data: [], isLoading: false })),
  useCreateEscalation: vi.fn(),
  useEscalationQueue: vi.fn(),
}));

describe("Mobile Bottom Navigation (C95)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    (useProfile as Mock).mockReturnValue({ data: null, isLoading: false });
    (useAppConfig as Mock).mockReturnValue({ data: { maintenance_mode: false }, isLoading: false });
    (useMyEscalations as Mock).mockReturnValue({ data: [], isLoading: false });
    vi.mocked(usePathname).mockReturnValue("/");
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams() as any);
  });

  it("renders 5 primary actions including Sign In when unauthenticated, with safe-area insets", () => {
    (useProfile as Mock).mockReturnValue({ data: null, isLoading: false });
    render(<Navbar />);

    const nav = document.querySelector("nav");
    expect(nav?.className).toContain("pt-[env(safe-area-inset-top,0px)]");

    const bottomNav = document.querySelector(".fixed.bottom-0");
    expect(bottomNav).toBeInTheDocument();
    expect(bottomNav?.className).toContain("pb-[env(safe-area-inset-bottom,0px)]");

    const homeLink = bottomNav?.querySelector('a[href="/"]');
    const scanLink = bottomNav?.querySelector('a[href="/scan"]');
    const collectionLink = bottomNav?.querySelector('a[href="/collection"]');
    const searchLink = bottomNav?.querySelector('a[href="/collection?focus=search"]');
    const loginLink = bottomNav?.querySelector('a[href="/login"]');

    expect(homeLink).toBeInTheDocument();
    expect(scanLink).toBeInTheDocument();
    expect(collectionLink).toBeInTheDocument();
    expect(searchLink).toBeInTheDocument();
    expect(loginLink).toBeInTheDocument();
  });

  it("renders Profile link in mobile bottom navigation when user is authenticated", () => {
    (useProfile as Mock).mockReturnValue({ data: { id: "1", display_name: "Ugg" }, isLoading: false });
    render(<Navbar />);

    const bottomNav = document.querySelector(".fixed.bottom-0");
    const profileLink = bottomNav?.querySelector('a[href="/profile"]');
    const loginLink = bottomNav?.querySelector('a[href="/login"]');

    expect(profileLink).toBeInTheDocument();
    expect(loginLink).toBeNull();
  });

  it("highlights the active tab corresponding to the current route", () => {
    vi.mocked(usePathname).mockReturnValue("/scan");
    render(<Navbar />);

    const bottomNav = document.querySelector(".fixed.bottom-0");
    const scanLink = bottomNav?.querySelector('a[href="/scan"]');
    expect(scanLink?.className).toContain("text-accent");
  });

  it("highlights search when on collection page with focus=search query parameter", () => {
    vi.mocked(usePathname).mockReturnValue("/collection");
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams("focus=search") as any);
    render(<Navbar />);

    const bottomNav = document.querySelector(".fixed.bottom-0");
    const searchLink = bottomNav?.querySelector('a[href="/collection?focus=search"]');
    expect(searchLink?.className).toContain("text-accent");

    const collectionLink = bottomNav?.querySelector('a[href="/collection"]');
    expect(collectionLink?.className).not.toContain("text-accent");
  });

  it("opens thumb search popup when tapping Search in bottom nav, allowing query input and submit", () => {
    const pushMock = vi.fn();
    vi.mocked(useRouter).mockReturnValue({
      push: pushMock,
      replace: vi.fn(),
      prefetch: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
    } as any);
    render(<Navbar />);

    const bottomNav = document.querySelector(".fixed.bottom-0");
    const searchLink = bottomNav?.querySelector('a[href="/collection?focus=search"]');
    expect(searchLink).toBeInTheDocument();

    // Popup is initially not open
    expect(screen.queryByRole("dialog")).toBeNull();

    // Tap search button
    fireEvent.click(searchLink!);

    // Popup is now visible
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(searchLink?.className).toContain("text-accent");

    // Type in search query
    const input = screen.getByTestId("thumb-search-input");
    fireEvent.change(input, { target: { value: "Tolkien" } });

    // Clear button appears and works
    const clearButton = screen.getByLabelText("Clear search");
    expect(clearButton).toBeInTheDocument();
    fireEvent.click(clearButton);
    expect((input as HTMLInputElement).value).toBe("");

    // Type query again and submit
    fireEvent.change(input, { target: { value: "Lem" } });
    const submitButton = dialog.querySelector('button[type="submit"]');
    fireEvent.click(submitButton!);

    // Should push to collection with search query and page 1
    expect(pushMock).toHaveBeenCalledWith("/collection?q=Lem&page=1");

    // Popup should close
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("closes thumb search popup when clicking close button or backdrop", () => {
    render(<Navbar />);

    const bottomNav = document.querySelector(".fixed.bottom-0");
    const searchLink = bottomNav?.querySelector('a[href="/collection?focus=search"]');

    fireEvent.click(searchLink!);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    // Close button dismisses
    const closeButton = screen.getByLabelText("Close search");
    fireEvent.click(closeButton);
    expect(screen.queryByRole("dialog")).toBeNull();

    // Reopen and close via backdrop
    fireEvent.click(searchLink!);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    const backdrop = screen.getByTestId("search-popup-backdrop");
    fireEvent.click(backdrop);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
