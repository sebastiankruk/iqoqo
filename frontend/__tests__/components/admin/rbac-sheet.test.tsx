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

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RbacSheet } from "@/components/admin/rbac-sheet";

vi.mock("@/lib/api/admin", () => ({
  getRoles: vi.fn(),
  updateUser: vi.fn(),
}));

import { getRoles, updateUser } from "@/lib/api/admin";
import { toast } from "sonner";

describe("RbacSheet", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getRoles).mockResolvedValue([{ id: 1, name: "user" }]);
  });

  it("reports successful role assignment and revocation saves", async () => {
    const user = { id: "user-1", email: "person@example.test", roles: ["user"], is_active: true };
    vi.mocked(updateUser).mockResolvedValueOnce(user);

    render(<RbacSheet user={user} onClose={vi.fn()} onUpdate={vi.fn()} canEdit />);
    await screen.findByText("user");
    fireEvent.click(screen.getByRole("button", { name: "Save Permissions" }));

    await waitFor(() => expect(updateUser).toHaveBeenCalledWith("user-1", { is_active: true, roles: ["user"] }));
    expect(toast.success).toHaveBeenCalledWith("User roles and permissions updated");
  });

  it("reports a failed role assignment or revocation", async () => {
    vi.mocked(updateUser).mockRejectedValueOnce(new Error("Permission update failed"));
    const user = { id: "user-1", email: "person@example.test", roles: [], is_active: true };

    render(<RbacSheet user={user} onClose={vi.fn()} onUpdate={vi.fn()} canEdit />);
    await screen.findByText("user");
    fireEvent.click(screen.getByRole("button", { name: "Save Permissions" }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Permission update failed"));
  });

  it("shows role-list load failures instead of fallback roles and retries", async () => {
    vi.mocked(getRoles).mockRejectedValueOnce(new Error("Role list unavailable"));
    const user = { id: "user-1", email: "person@example.test", roles: ["user"], is_active: true };

    render(<RbacSheet user={user} onClose={vi.fn()} onUpdate={vi.fn()} canEdit />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load available roles: Role list unavailable");
    expect(screen.queryByText("custodian")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Permissions" })).toBeDisabled();
    expect(toast.error).toHaveBeenCalledWith("Role list unavailable");

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("user")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Permissions" })).toBeEnabled();
  });
});
