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

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Navbar } from "@/components/dashboard/navbar";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

const mockConfig = {
  data: {
    federation_enabled: true,
    federation_head_mode: true,
    version: "1.0.2",
    maintenance_mode: false,
  },
};

vi.mock("@/lib/api/hooks/catalog", () => ({
  useAppConfig: () => mockConfig,
}));

vi.mock("@/lib/api/hooks", () => ({
  useAppConfig: () => mockConfig,
  useProfile: () => ({
    data: {
      id: "u1",
      email: "user@iqoqo.local",
      display_name: "Test User",
      roles: ["user"],
      permissions: [],
    },
    isLoading: false,
  }),
  useMyEscalations: () => ({ data: [] }),
}));

vi.mock("@/lib/api/escalations", () => ({
  useMyEscalations: () => ({ data: [] }),
}));

vi.mock("@/components/dashboard/notification-center", () => ({
  NotificationCenter: () => <div data-testid="notification-center" />,
}));

vi.mock("@/components/mode-toggle", () => ({
  ModeToggle: () => <div data-testid="mode-toggle" />,
}));

vi.mock("@/components/language-toggle", () => ({
  LanguageToggle: () => <div data-testid="language-toggle" />,
}));

/**
 * Helper to render components wrapped in a React Query provider.
 *
 * @param ui - Component element to render.
 * @returns Render result from Testing Library.
 */
function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("Navbar Federation Head Mode", () => {
  beforeEach(() => {
    mockConfig.data.federation_head_mode = true;
    window.sessionStorage.clear();
  });

  it("renders Federation Hub badge in navbar", () => {
    renderWithClient(<Navbar />);
    expect(screen.getByTestId("federation-hub-badge")).toBeInTheDocument();
  });

  it("renders dismissible Federation Hub banner and dismisses on click", () => {
    renderWithClient(<Navbar />);
    const banner = screen.getByTestId("federation-head-banner");
    expect(banner).toBeInTheDocument();

    const dismissBtn = screen.getByLabelText(/Dismiss banner/i);
    fireEvent.click(dismissBtn);

    expect(screen.queryByTestId("federation-head-banner")).not.toBeInTheDocument();
  });

  it("replaces Scan CTA with Directory in desktop and mobile bottom navigation", () => {
    renderWithClient(<Navbar />);
    // Desktop Scan button should NOT be rendered
    expect(screen.queryByRole("link", { name: /^Scan$/i })).not.toBeInTheDocument();

    // Directory link should be present
    const directoryLinks = screen.getAllByRole("link", { name: /Directory/i });
    expect(directoryLinks.length).toBeGreaterThan(0);
  });
});
