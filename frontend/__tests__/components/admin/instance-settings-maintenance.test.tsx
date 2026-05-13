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
import { describe, it, expect, vi, beforeEach } from "vitest";
import { InstanceSettings } from "@/components/admin/instance-settings";
import * as adminApi from "@/lib/api/admin";

vi.mock("@/lib/api/admin");

describe("InstanceSettings - Maintenance Mode", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders Maintenance Mode toggle in internal category", async () => {
    vi.mocked(adminApi.getInstanceSettings).mockResolvedValue({
      MAINTENANCE_MODE: { value: "false", source: "db" },
      IQOQO_KNOWN_JUNK_PHASHES: { value: "", source: "missing" },
    });

    render(<InstanceSettings category="internal" />);

    await waitFor(() => {
      expect(screen.getByText(/Maintenance Mode/i)).toBeDefined();
    });

    const select = screen.getByRole("combobox");
    expect(select).toBeDefined();
    expect((select as HTMLSelectElement).value).toBe("false");
  });
});
