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

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

import { getRoles, getPermissions, getRolePermissions, createRole, deleteRole, updateRolePermissions } from "@/lib/api/admin";
import { toast } from "sonner";

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

  it("shows an initial role and permission load failure and retries instead of showing an empty list", async () => {
    vi.mocked(getRoles).mockRejectedValueOnce(new Error("Role list unavailable"));
    render(<GroupManagement canEdit />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load roles and permissions");
    expect(screen.queryByText("No roles")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add Role" })).not.toBeInTheDocument();
    expect(toast.error).toHaveBeenCalledWith("Role list unavailable");

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("admin")).toBeInTheDocument();
  });

  it("does not treat a failed permission catalog load as an empty authoritative list", async () => {
    vi.mocked(getPermissions).mockRejectedValueOnce(new Error("Permission catalog unavailable"));
    render(<GroupManagement canEdit />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load roles and permissions");
    expect(screen.queryByRole("button", { name: "Add Role" })).not.toBeInTheDocument();
    expect(toast.error).toHaveBeenCalledWith("Permission catalog unavailable");

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("admin")).toBeInTheDocument();
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

  it("opens an accessible dialog and creates a role with success feedback", async () => {
    vi.mocked(createRole).mockResolvedValueOnce({ id: 4, name: "editor" });
    render(<GroupManagement canEdit />);

    fireEvent.click(await screen.findByRole("button", { name: "Add Role" }));
    const dialog = await screen.findByRole("dialog", { name: "Add New Role" });
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveClass("max-h-[calc(100dvh-2rem)]");

    expect(screen.getByRole("textbox", { name: "Role Name" })).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("e.g., moderator, editor"), { target: { value: "editor" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Role" }));

    await waitFor(() => expect(createRole).toHaveBeenCalledWith("editor"));
    expect(toast.success).toHaveBeenCalledWith('Role "editor" created');
  });

  it("shows feedback when role permissions are saved", async () => {
    vi.mocked(updateRolePermissions).mockResolvedValueOnce({ role_id: 3, role_name: "custodian", permission_ids: [1] });
    render(<GroupManagement canEdit />);

    fireEvent.click(await screen.findByText("custodian"));
    fireEvent.click(await screen.findByRole("button", { name: "Save Changes" }));

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("Role permissions saved"));
  });

  it("shows a rejection toast when saving role permissions fails", async () => {
    vi.mocked(updateRolePermissions).mockRejectedValueOnce(new Error("Permission save failed"));
    render(<GroupManagement canEdit />);

    fireEvent.click(await screen.findByText("custodian"));
    fireEvent.click(await screen.findByRole("button", { name: "Save Changes" }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Permission save failed"));
  });

  it("shows permission-load errors, disables saving, and lets the user retry", async () => {
    vi.mocked(getRolePermissions).mockRejectedValueOnce(new Error("Permission load failed"));
    render(<GroupManagement canEdit />);

    fireEvent.click(await screen.findByText("custodian"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load permissions for this role.");
    expect(toast.error).toHaveBeenCalledWith("Permission load failed");
    expect(screen.getByRole("button", { name: "Save Changes" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByText("delete:item");
    expect(getRolePermissions).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("button", { name: "Save Changes" })).toBeEnabled();
  });

  it("keeps the create dialog open and disables dismissal while creating", async () => {
    let resolveCreate: ((role: { id: number; name: string }) => void) | undefined;
    const pendingCreate = new Promise<{ id: number; name: string }>(resolve => {
      resolveCreate = resolve;
    });
    vi.mocked(createRole).mockReturnValueOnce(pendingCreate);
    render(<GroupManagement canEdit />);

    fireEvent.click(await screen.findByRole("button", { name: "Add Role" }));
    const dialog = await screen.findByRole("dialog", { name: "Add New Role" });
    fireEvent.change(screen.getByRole("textbox", { name: "Role Name" }), { target: { value: "editor" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Role" }));

    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Close" })).toBeDisabled();
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.getByRole("dialog", { name: "Add New Role" })).toBeInTheDocument();

    resolveCreate?.({ id: 4, name: "editor" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Add New Role" })).not.toBeInTheDocument());
  });

  it("keeps the delete dialog open and prevents dismissal while deleting", async () => {
    let resolveDelete: (() => void) | undefined;
    const pendingDelete = new Promise<void>(resolve => {
      resolveDelete = resolve;
    });
    vi.mocked(deleteRole).mockReturnValueOnce(pendingDelete);
    render(<GroupManagement canEdit />);

    fireEvent.click(await screen.findByText("custodian"));
    fireEvent.click(await screen.findByRole("button", { name: "Delete Role" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete Role" });
    fireEvent.click(screen.getByRole("button", { name: /^Delete$/ }));

    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Close" })).toBeDisabled();
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.getByRole("dialog", { name: "Delete Role" })).toBeInTheDocument();

    resolveDelete?.();
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Delete Role" })).not.toBeInTheDocument());
  });

  it("shows a rejection toast and preserves the delete dialog when role deletion fails", async () => {
    vi.mocked(deleteRole).mockRejectedValueOnce(new Error("Role deletion failed"));
    render(<GroupManagement canEdit />);

    fireEvent.click(await screen.findByText("custodian"));
    fireEvent.click(await screen.findByRole("button", { name: "Delete Role" }));
    fireEvent.click(await screen.findByRole("button", { name: /^Delete$/ }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Role deletion failed"));
    expect(screen.getByRole("dialog", { name: "Delete Role" })).toBeInTheDocument();
    expect(screen.getByText("custodian")).toBeInTheDocument();
  });

  it("shows a rejection toast and keeps the create dialog open when creation fails", async () => {
    vi.mocked(createRole).mockRejectedValueOnce(new Error("Role creation failed"));
    render(<GroupManagement canEdit />);

    fireEvent.click(await screen.findByRole("button", { name: "Add Role" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Role Name" }), { target: { value: "editor" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Role" }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Role creation failed"));
    expect(screen.getByRole("dialog", { name: "Add New Role" })).toBeInTheDocument();
  });
});
