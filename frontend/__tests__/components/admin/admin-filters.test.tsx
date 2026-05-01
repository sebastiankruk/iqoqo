// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { UserManagement } from "@/components/admin/user-management";
import * as adminApi from "@/lib/api/admin";

vi.mock("@/lib/api/admin");

describe("AdminFilters via UserManagement", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminApi.getUsers).mockResolvedValue({
      data: [{ id: "1", email: "alice@test.com", display_name: "Alice", roles: ["user"], is_active: true }],
      meta: { total: 1, page: 1, pages: 1 },
    });
  });

  it("renders the filter select and invokes API on status change", async () => {
    render(<UserManagement canEdit />);

    await waitFor(() => {
      expect(screen.getByText("alice@test.com")).toBeInTheDocument();
    });

    const statusSelect = screen.getByRole("combobox");
    expect(statusSelect).toBeInTheDocument();

    fireEvent.change(statusSelect, { target: { value: "inactive" } });

    await waitFor(() => {
      expect(adminApi.getUsers).toHaveBeenCalledWith(expect.objectContaining({ status: "inactive" }));
    });
  });
});
