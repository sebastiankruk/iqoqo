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
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import FederationDirectoryPage from "@/app/federation/directory/page";
import * as federationApi from "@/lib/api/federation";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, unknown>) => {
    if (params?.count !== undefined) return `${params.count} public items tracked`;
    return key;
  },
  useLocale: () => "en",
}));

vi.mock("@/components/dashboard/navbar", () => ({
  Navbar: () => <nav data-testid="navbar">Navbar</nav>,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer">Footer</footer>,
}));

describe("FederationDirectoryPage", () => {
  it("renders local instance information and peer libraries", async () => {
    vi.spyOn(federationApi, "getFederationDirectory").mockResolvedValueOnce({
      local_instance: {
        domain: "local.library.example",
        software_name: "iqoqo",
        software_version: "0.9.2",
        public_items_count: 42,
      },
      peers: [
        {
          id: 1,
          domain: "peer.galaxy.example",
          software_name: "iqoqo",
          software_version: "0.9.1",
          trust_level: "trusted",
          shared_inbox_url: null,
          last_seen_at: "2026-10-21T12:00:00Z",
          created_at: "2026-10-20T12:00:00Z",
        },
      ],
      total_peers: 1,
    });

    render(<FederationDirectoryPage />);

    expect(screen.getByTestId("navbar")).toBeInTheDocument();
    expect(screen.getByTestId("footer")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("local.library.example")).toBeInTheDocument();
      expect(screen.getByText("peer.galaxy.example")).toBeInTheDocument();
      expect(screen.getByText("trusted")).toBeInTheDocument();
    });
  });
});
