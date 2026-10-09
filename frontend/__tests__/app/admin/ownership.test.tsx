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
import OwnershipPage from "@/app/admin/ownership/page";
import { useProfile } from "@/lib/api/hooks";
import * as adminApi from "@/lib/api/admin";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { UserProfile } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

vi.mock("@/lib/api/admin", () => ({
  getOwnershipAccounts: vi.fn(),
  getOwnershipItems: vi.fn(),
  previewOwnershipReassignment: vi.fn(),
  executeOwnershipReassignment: vi.fn(),
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));

function mockProfile(roles: string[], permissions: string[]) {
  vi.mocked(useProfile).mockReturnValue({
    data: {
      id: "admin-1",
      email: "admin@example.com",
      roles,
      permissions,
    } as unknown as UserProfile,
    isLoading: false,
  } as unknown as ReturnType<typeof useProfile>);
}

const mockAccounts: adminApi.OwnershipAccount[] = [
  {
    id: "user-1",
    email: "alice@example.com",
    username: "alice",
    display_name: "Alice A",
    is_active: true,
  },
  {
    id: "user-2",
    email: "bob@example.com",
    username: "bob",
    display_name: "Bob B",
    is_active: true,
  },
];

const mockItems: adminApi.OwnershipSourceItem[] = [
  {
    id: 101,
    title: "The Hobbit",
    format: "Hardcover",
    is_hidden: false,
  },
  {
    id: 102,
    title: "1984",
    format: "Paperback",
    is_hidden: true,
  },
];

describe("OwnershipPage and OwnershipManagement UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Access Restricted when missing write:users permission or admin role", () => {
    mockProfile(["admin"], ["read:users"]); // missing write:users

    render(<OwnershipPage />);

    expect(screen.getByText("Access Restricted")).toBeInTheDocument();
    expect(screen.queryByText("Account Selection")).not.toBeInTheDocument();
  });

  it("renders full ownership UI when authorized with admin role and write:users", async () => {
    mockProfile(["admin"], ["read:users", "write:users"]);
    vi.mocked(adminApi.getOwnershipAccounts).mockResolvedValue(mockAccounts);

    render(<OwnershipPage />);

    expect(screen.getByText("Item Ownership Reassignment")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByLabelText(/Source Account/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Target Account/i)).toBeInTheDocument();
    });
  });

  it("loads source items when source account selected and supports single transfer preview", async () => {
    mockProfile(["admin"], ["read:users", "write:users"]);
    vi.mocked(adminApi.getOwnershipAccounts).mockResolvedValue(mockAccounts);
    vi.mocked(adminApi.getOwnershipItems).mockResolvedValue({
      items: mockItems,
      total: 2,
      pages: 1,
    });
    vi.mocked(adminApi.previewOwnershipReassignment).mockResolvedValue({
      source: { id: "user-1", username: "alice", display_name: "Alice A" },
      target: { id: "user-2", username: "bob", display_name: "Bob B" },
      mode: "single",
      item_ids: [101],
      total_count: 1,
      hidden_count: 0,
      lent_count: 0,
      fingerprint: "hash-101",
    });

    render(<OwnershipPage />);

    await waitFor(() => screen.getByLabelText(/Source Account/i));

    // Select source account
    fireEvent.change(screen.getByLabelText(/Source Account/i), {
      target: { value: "user-1" },
    });

    // Select target account
    fireEvent.change(screen.getByLabelText(/Target Account/i), {
      target: { value: "user-2" },
    });

    // Verify items loaded
    await waitFor(() => {
      expect(screen.getByText("The Hobbit")).toBeInTheDocument();
      expect(screen.getByText("1984")).toBeInTheDocument();
    });

    // Click single item transfer button on first item
    const transferButtons = screen.getAllByRole("button", { name: /Transfer/i });
    // First transfer button in table
    fireEvent.click(transferButtons[2]); // index 0 is Transfer Selected, 1 is Transfer All, 2 is row 101

    await waitFor(() => {
      expect(screen.getByText("Confirm Ownership Reassignment")).toBeInTheDocument();
      expect(screen.getByText(/hash-101|SINGLE/i)).toBeInTheDocument();
    });
  });

  it("requires affirmative acknowledgement checkbox for all-scope transfer", async () => {
    mockProfile(["admin"], ["read:users", "write:users"]);
    vi.mocked(adminApi.getOwnershipAccounts).mockResolvedValue(mockAccounts);
    vi.mocked(adminApi.getOwnershipItems).mockResolvedValue({
      items: mockItems,
      total: 2,
      pages: 1,
    });
    vi.mocked(adminApi.previewOwnershipReassignment).mockResolvedValue({
      source: { id: "user-1", username: "alice", display_name: "Alice A" },
      target: { id: "user-2", username: "bob", display_name: "Bob B" },
      mode: "all",
      item_ids: [101, 102],
      total_count: 2,
      hidden_count: 1,
      lent_count: 0,
      fingerprint: "hash-all-2",
    });

    render(<OwnershipPage />);

    await waitFor(() => screen.getByLabelText(/Source Account/i));

    fireEvent.change(screen.getByLabelText(/Source Account/i), {
      target: { value: "user-1" },
    });
    fireEvent.change(screen.getByLabelText(/Target Account/i), {
      target: { value: "user-2" },
    });

    await waitFor(() => screen.getByText("The Hobbit"));

    // Click "Transfer All Source Items (2)"
    fireEvent.click(screen.getByRole("button", { name: /Transfer All Source Items/i }));

    await waitFor(() => {
      expect(screen.getByText("Confirm Ownership Reassignment")).toBeInTheDocument();
    });

    const confirmButton = screen.getByRole("button", { name: /Confirm Reassignment/i });
    expect(confirmButton).toBeDisabled();

    // Check affirmative checkbox
    const ackCheckbox = screen.getByRole("checkbox", {
      name: /I explicitly confirm reassigning/i,
    });
    fireEvent.click(ackCheckbox);

    expect(confirmButton).not.toBeDisabled();
  });
});
