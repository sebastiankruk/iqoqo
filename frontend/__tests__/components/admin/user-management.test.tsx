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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { UserManagement } from "@/components/admin/user-management";
import * as adminApi from "@/lib/api/admin";

// Mock the API layer entirely
vi.mock("@/lib/api/admin");

describe("UserManagement Component", () => {
  const mockUsers = [
    { id: "1", email: "test1@test.com", display_name: "Test One", roles: ["user"], is_active: true },
    { id: "2", email: "test2@test.com", display_name: "Test Two", roles: ["admin"], is_active: false },
  ];

  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminApi.getUsers).mockResolvedValue({
      data: mockUsers,
      meta: { total: 2, page: 1, pages: 1 },
    });
    vi.mocked(adminApi.getRoles).mockResolvedValue([
      { id: 1, name: "admin" },
      { id: 2, name: "custodian" },
      { id: 3, name: "user" },
    ]);
  });

  it("renders table and loads users automatically", async () => {
    render(<UserManagement canEdit />);

    // Shows loading state initially
    expect(screen.getByRole("table")).toBeInTheDocument();

    // Waits for users to load and populate the DOM
    await waitFor(() => {
      expect(screen.getByText("test1@test.com")).toBeInTheDocument();
      expect(screen.getByText("test2@test.com")).toBeInTheDocument();
    });

    // Verifies roles and status badges are rendered correctly
    expect(screen.getAllByText("Active").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Suspended").length).toBeGreaterThan(0);
  });

  it("triggers search filter on input change (debounced)", async () => {
    render(<UserManagement canEdit />);
    await waitFor(() => expect(screen.getByText("test1@test.com")).toBeInTheDocument());

    const searchInput = screen.getByPlaceholderText("Search users...");
    fireEvent.change(searchInput, { target: { value: "test2" } });

    // Wait for the 300ms debounce
    await waitFor(() => {
      expect(adminApi.getUsers).toHaveBeenCalledWith(expect.objectContaining({ search: "test2", status: "all" }));
    });
  });

  it("opens RBAC sheet on user row click when canEdit is true", async () => {
    render(<UserManagement canEdit />);
    await waitFor(() => expect(screen.getByText("test1@test.com")).toBeInTheDocument());

    // Click the table row
    await waitFor(() => {
      fireEvent.click(screen.getByText("test1@test.com"));
    });

    // Assert the Sheet slide-over mounts
    expect(screen.getByText("User Access Control")).toBeInTheDocument();
    expect(screen.getByText("Save Permissions")).toBeInTheDocument();
  });
});
