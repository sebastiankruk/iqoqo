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
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { InstanceSettings } from "@/components/admin/instance-settings";
import * as adminApi from "@/lib/api/admin";

vi.mock("@/lib/api/admin");

describe("InstanceSettings - Target Secrets Mask & Reveal", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders target secrets and handles mask and reveal actions", async () => {
    const user = userEvent.setup();

    vi.mocked(adminApi.getInstanceSettings).mockResolvedValue({
      TMDB_API_READ_ACCESS_TOKEN: { value: "***1234", source: "db" },
      DISCOGS_CONSUMER_SECRET: { value: "***abcd", source: "db" },
      UPC_ITEM_DB_KEY: { value: "***5678", source: "db" },
      IGDB_CLIENT_SECRET: { value: "***9999", source: "db" },
    });

    vi.mocked(adminApi.revealSettingValue).mockImplementation(async (key: string) => {
      if (key === "TMDB_API_READ_ACCESS_TOKEN") return { success: true, key, value: "tmdb-secret-bearer-token-1234" };
      if (key === "DISCOGS_CONSUMER_SECRET") return { success: true, key, value: "discogs-consumer-secret-abcd" };
      if (key === "UPC_ITEM_DB_KEY") return { success: true, key, value: "upc-item-db-key-5678" };
      if (key === "IGDB_CLIENT_SECRET") return { success: true, key, value: "igdb-client-secret-9999" };
      return { success: true, key, value: "revealed-secret" };
    });

    render(<InstanceSettings category="external_apis" showApiKeys={true} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Enter TMDB read access token")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Enter Discogs Consumer Secret")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Enter UPCItemDB key")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Enter IGDB Client Secret")).toBeInTheDocument();
    });

    // Check masked values are displayed
    const tmdbInput = screen.getByPlaceholderText("Enter TMDB read access token") as HTMLInputElement;
    expect(tmdbInput.value).toBe("***1234");

    // Reveal TMDB token
    const revealButtons = screen.getAllByTitle("Reveal stored value");
    expect(revealButtons.length).toBeGreaterThan(0);

    // Find the reveal button corresponding to TMDB input
    const tmdbContainer = tmdbInput.closest(".relative");
    const tmdbRevealBtn = tmdbContainer?.querySelector('button[title="Reveal stored value"]');
    expect(tmdbRevealBtn).not.toBeNull();

    await user.click(tmdbRevealBtn!);

    await waitFor(() => {
      expect(adminApi.revealSettingValue).toHaveBeenCalledWith("TMDB_API_READ_ACCESS_TOKEN");
      expect(tmdbInput.value).toBe("tmdb-secret-bearer-token-1234");
    });

    // Hide it again
    const tmdbHideBtn = tmdbContainer?.querySelector('button[title="Hide value"]');
    expect(tmdbHideBtn).not.toBeNull();
    await user.click(tmdbHideBtn!);

    await waitFor(() => {
      expect(tmdbInput.value).toBe("***1234");
    });
  });
});
