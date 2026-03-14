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
import { render, screen } from "@testing-library/react";
import AdminSettingsPage from "@/app/admin/settings/page";
import { useProfile } from "@/lib/api/hooks";
import { useRouter } from "next/navigation";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { UserProfile } from "@/types/frbr";

// Mock dependencies
vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

describe("AdminSettingsPage", () => {
  const mockPush = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({ push: mockPush } as unknown as ReturnType<typeof useRouter>);
  });

  it("shows a loading state initially", () => {
    vi.mocked(useProfile).mockReturnValue({ data: undefined, isLoading: true } as unknown as ReturnType<typeof useProfile>);

    render(<AdminSettingsPage />);

    // Page title should not be visible while loading
    expect(screen.queryByText("Admin Settings")).toBeNull();
  });

  it("redirects non-admin users to the home page", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: { id: "1", email: "user@test.com", roles: ["user"] } as unknown as UserProfile,
      isLoading: false
    } as unknown as ReturnType<typeof useProfile>);

    render(<AdminSettingsPage />);

    // Should trigger redirect
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("renders the admin dashboard and sidebar tabs for admin users", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: { id: "2", email: "admin@test.com", roles: ["admin"] } as unknown as UserProfile,
      isLoading: false
    } as unknown as ReturnType<typeof useProfile>);

    render(<AdminSettingsPage />);

    // Should not redirect
    expect(mockPush).not.toHaveBeenCalled();

    // Should render main layout elements
    expect(screen.getByRole("heading", { name: "Admin Settings", level: 1 })).toBeInTheDocument();

    // Should render sidebar navigation buttons
    expect(screen.getByText("Instance Settings")).toBeInTheDocument();
    expect(screen.getByText("User Management")).toBeInTheDocument();
    expect(screen.getByText("Integrations & Monetization")).toBeInTheDocument();
  });
});
