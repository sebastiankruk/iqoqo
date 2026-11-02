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
import { render } from "@testing-library/react";
import { describe, it, expect, vi, type Mock, beforeEach } from "vitest";
import { Navbar } from "@/components/dashboard/navbar";
import { useProfile, useAppConfig } from "@/lib/api/hooks";
import { useMyEscalations } from "@/lib/api/escalations";
import { usePathname, useSearchParams } from "next/navigation";

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

  it("renders 4 primary actions: Home, Scan, Collection, Search on all screen sizes", () => {
    render(<Navbar />);

    const bottomNav = document.querySelector(".fixed.bottom-0");
    expect(bottomNav).toBeInTheDocument();

    const homeLink = bottomNav?.querySelector('a[href="/"]');
    const scanLink = bottomNav?.querySelector('a[href="/scan"]');
    const collectionLink = bottomNav?.querySelector('a[href="/collection"]');
    const searchLink = bottomNav?.querySelector('a[href="/collection?focus=search"]');

    expect(homeLink).toBeInTheDocument();
    expect(scanLink).toBeInTheDocument();
    expect(collectionLink).toBeInTheDocument();
    expect(searchLink).toBeInTheDocument();
  });

  it("never renders a login or sign-in link inside the mobile bottom navigation bar", () => {
    (useProfile as Mock).mockReturnValue({ data: null, isLoading: false });
    render(<Navbar />);

    const bottomNav = document.querySelector(".fixed.bottom-0");
    const loginLink = bottomNav?.querySelector('a[href="/login"]');
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
});
