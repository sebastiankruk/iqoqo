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
import { vi, describe, it, expect, beforeEach } from "vitest";
import { GroupManagement } from "@/components/admin/group-management";

vi.mock("@/lib/api/admin", () => ({
  getRoles: vi.fn(),
  getPermissions: vi.fn(),
  getRolePermissions: vi.fn(),
  updateRolePermissions: vi.fn(),
  createRole: vi.fn(),
  deleteRole: vi.fn(),
}));

import { getRoles, getPermissions, getRolePermissions } from "@/lib/api/admin";

vi.mocked(getRoles).mockResolvedValue([
  { id: 1, name: "admin", is_protected: true, member_count: 2 },
  { id: 2, name: "user", is_protected: true, member_count: 5 },
  { id: 3, name: "custodian", is_protected: false, member_count: 1 },
]);

vi.mocked(getPermissions).mockResolvedValue([
  { id: 1, name: "delete:item", description: "Allow deletion of items" },
  { id: 2, name: "regenerate:cover", description: "Allow regenerating covers" },
]);

vi.mocked(getRolePermissions).mockResolvedValue({ role_id: 3, role_name: "custodian", permission_ids: [1] });

describe("GroupManagement Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders roles with member counts", async () => {
    render(<GroupManagement canEdit />);

    // Wait for roles to load
    await waitFor(() => {
      expect(screen.getByText("admin")).toBeInTheDocument();
    });

    // Check member counts are displayed
    expect(screen.getByText("2 users")).toBeInTheDocument();
    expect(screen.getByText("5 users")).toBeInTheDocument();
  });

  it("shows protected badge for protected roles", async () => {
    render(<GroupManagement canEdit />);

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByText("admin")).toBeInTheDocument();
    });

    // Check that Protected badge appears
    const protectedBadges = await screen.findAllByText("Protected");
    expect(protectedBadges.length).toBeGreaterThan(0);
  });

  it("shows add role button when canEdit is true", async () => {
    render(<GroupManagement canEdit />);

    await waitFor(() => {
      expect(screen.getByText("Add Role")).toBeInTheDocument();
    });
  });
});
