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

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ScanPage from "@/app/scan/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => "/scan",
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
  useAddManualItem: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  queryKeys: {
    itemsAll: ["items"],
  },
}));

vi.mock("@/lib/api/escalations", () => ({
  useCreateNewMediaTypeEscalation: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
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

describe("ScanPage Federation Head Mode", () => {
  beforeEach(() => {
    mockConfig.data.federation_head_mode = true;
  });

  it("renders Federation Hub notice card on /scan when federation_head_mode is enabled", () => {
    renderWithClient(<ScanPage />);

    expect(screen.getByTestId("federation-head-scan-notice")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Read-Only Federation Hub/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Explore Federated Catalog/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Connected Libraries/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Wishlist/i })).toBeInTheDocument();
  });
});
