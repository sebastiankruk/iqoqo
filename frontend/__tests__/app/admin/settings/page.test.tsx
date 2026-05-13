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
import SettingsHubPage from "@/app/admin/settings/page";
import { useProfile } from "@/lib/api/hooks";
import { useRouter } from "next/navigation";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { UserProfile } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
  useAppConfig: vi.fn(() => ({ data: { maintenance_mode: false }, isLoading: false })),
}));

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}));

vi.mock("@/components/admin/instance-settings", () => ({
  InstanceSettings: () => <div data-testid="instance-settings" />,
}));

vi.mock("@/components/admin/user-management", () => ({
  UserManagement: () => <div data-testid="user-management" />,
}));

describe("SettingsHubPage", () => {
  const mockPush = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({ push: mockPush } as unknown as ReturnType<typeof useRouter>);
  });

  it("shows a loading state initially", () => {
    vi.mocked(useProfile).mockReturnValue({ data: undefined, isLoading: true } as unknown as ReturnType<
      typeof useProfile
    >);

    render(<SettingsHubPage />);
    expect(screen.queryByRole("heading", { name: "Profile Settings" })).toBeNull();
  });

  it("renders profile settings for standard users", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: { id: "1", email: "user@test.com", display_name: "Test User", roles: ["user"] } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    expect(mockPush).not.toHaveBeenCalled();
    expect(await screen.findByRole("heading", { name: "Profile Settings", level: 1 })).toBeInTheDocument();

    expect(screen.getByRole("button", { name: "Profile" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Settings" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Users" })).not.toBeInTheDocument();
  });

  it("renders admin tabs and allows switching for admins", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "2",
        email: "admin@test.com",
        display_name: "Admin User",
        roles: ["admin"],
        permissions: [
          "config:external_apis",
          "config:federation",
          "config:affiliate",
          "config:internal",
          "read:users",
          "write:users",
          "read:roles",
          "write:roles",
        ],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    expect(mockPush).not.toHaveBeenCalled();
    expect(await screen.findByRole("heading", { name: "Profile Settings", level: 1 })).toBeInTheDocument();

    expect(screen.getByRole("button", { name: "Profile" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "API Integrations" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Users" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Roles" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Security" })).toBeInTheDocument();
  });
});
