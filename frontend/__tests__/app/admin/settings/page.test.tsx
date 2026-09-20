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

vi.mock("@/components/collection/manage-collections-modal", () => ({
  ManageCollectionsModal: () => null,
}));

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
  useAppConfig: vi.fn(() => ({ data: { maintenance_mode: false }, isLoading: false })),
}));

vi.mock("@/lib/api/escalations", () => ({
  useMyEscalations: vi.fn(() => ({ data: [], isLoading: false })),
  useCreateEscalation: vi.fn(),
  useEscalationQueue: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: vi.fn(),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}));

vi.mock("@/components/admin/instance-settings", () => ({
  InstanceSettings: () => <div data-testid="instance-settings" />,
}));

vi.mock("@/components/admin/user-management", () => ({
  UserManagement: () => <div data-testid="user-management" />,
}));

vi.mock("@/components/escalation/my-escalations", () => ({
  MyEscalations: () => <div data-testid="my-escalations">My Escalations</div>,
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
    expect(screen.queryByRole("heading", { name: "Instance Settings" })).toBeNull();
  });

  it("redirects non-admin users to /profile", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: { id: "1", email: "user@test.com", display_name: "Test User", roles: ["user"] } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // Non-admin users should be redirected to /profile
    expect(mockPush).toHaveBeenCalledWith("/profile");
  });

  it("renders admin tabs for admins without Profile tab", async () => {
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

    // Admin should NOT be redirected
    expect(mockPush).not.toHaveBeenCalled();

    // Admin should see Instance Settings as default tab (not Profile Settings)
    expect(await screen.findByRole("heading", { name: "Instance Settings", level: 1 })).toBeInTheDocument();

    // Profile tab should NOT exist in admin settings
    expect(screen.queryByRole("button", { name: "Profile" })).not.toBeInTheDocument();

    // Admin tabs should be visible
    expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "API Integrations" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Users" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Roles" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Security" })).toBeInTheDocument();
  });

  // ── Regression: Custodian permission format (colon vs underscore) ────────
  // These tests prevent the bug where custodian users were redirected to /profile
  // because the frontend checked for underscore-format permissions (write_metadata)
  // while the backend returns colon-format permissions (write:metadata).

  it("does NOT redirect custodian users with colon-format permissions to /profile (regression)", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "3",
        email: "custodian@test.com",
        display_name: "Test Custodian",
        roles: ["user", "custodian"],
        permissions: ["write:metadata", "read:metadata", "edit:cover", "escalate:resolve"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // Custodian with colon-format permissions should NOT be redirected to /profile
    expect(mockPush).not.toHaveBeenCalledWith("/profile");
  });

  it("does NOT redirect users with only write:metadata permission (regression)", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "4",
        email: "metadata-writer@test.com",
        display_name: "Metadata Writer",
        roles: ["user"],
        permissions: ["write:metadata"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // User with write:metadata should NOT be redirected to /profile
    expect(mockPush).not.toHaveBeenCalledWith("/profile");
  });

  it("does NOT redirect users with only edit:cover permission (regression)", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "5",
        email: "cover-editor@test.com",
        display_name: "Cover Editor",
        roles: ["user"],
        permissions: ["edit:cover"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // User with edit:cover should NOT be redirected to /profile
    expect(mockPush).not.toHaveBeenCalledWith("/profile");
  });

  it("does NOT redirect users with only escalate:resolve permission (regression)", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "6",
        email: "escalation-resolver@test.com",
        display_name: "Escalation Resolver",
        roles: ["user"],
        permissions: ["escalate:resolve"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // User with escalate:resolve should NOT be redirected to /profile
    expect(mockPush).not.toHaveBeenCalledWith("/profile");
  });

  it("does NOT redirect users with only read:metadata permission (regression)", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "7",
        email: "metadata-reader@test.com",
        display_name: "Metadata Reader",
        roles: ["user"],
        permissions: ["read:metadata"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // User with read:metadata should NOT be redirected to /profile
    expect(mockPush).not.toHaveBeenCalledWith("/profile");
  });

  it("redirects users with underscore-format permissions to /profile (negative regression)", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "8",
        email: "underscore-user@test.com",
        display_name: "Underscore User",
        roles: ["user"],
        // Wrong format - underscore instead of colon - should NOT grant access
        permissions: ["write_metadata", "edit_cover", "escalate_resolve", "read_metadata"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // User with underscore-format permissions should be redirected to /profile
    // because the frontend correctly checks for colon-format only
    expect(mockPush).toHaveBeenCalledWith("/profile");
  });

  it("redirects regular users without custodian permissions to /profile", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "9",
        email: "regular@test.com",
        display_name: "Regular User",
        roles: ["user"],
        permissions: ["read:owners", "write:item"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // Regular user without custodian permissions should be redirected
    expect(mockPush).toHaveBeenCalledWith("/profile");
  });

  it("renders custodian sidebar for users with write:metadata permission", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "10",
        email: "custodian-sidebar@test.com",
        display_name: "Custodian Sidebar",
        roles: ["user"],
        permissions: ["write:metadata"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // Custodian should NOT be redirected
    expect(mockPush).not.toHaveBeenCalledWith("/profile");

    // Custodian should see the Metadata nav item
    expect(screen.getByText("Metadata")).toBeInTheDocument();
  });

  it("renders custodian sidebar for users with edit:cover permission", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "11",
        email: "cover-custodian@test.com",
        display_name: "Cover Custodian",
        roles: ["user"],
        permissions: ["edit:cover"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // Custodian should NOT be redirected
    expect(mockPush).not.toHaveBeenCalledWith("/profile");

    // Custodian should see the Cover Art nav item
    expect(screen.getByText("Cover Art")).toBeInTheDocument();
  });

  it("renders custodian sidebar for users with escalate:resolve permission", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "12",
        email: "escalation-custodian@test.com",
        display_name: "Escalation Custodian",
        roles: ["user"],
        permissions: ["escalate:resolve"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // Custodian should NOT be redirected
    expect(mockPush).not.toHaveBeenCalledWith("/profile");

    // Custodian should see the User Requests nav item
    expect(screen.getByText("User Requests")).toBeInTheDocument();
  });

  it("renders SPARQL Explorer for users with read:metadata permission", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "13",
        email: "sparql-reader@test.com",
        display_name: "SPARQL Reader",
        roles: ["user"],
        permissions: ["read:metadata"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<SettingsHubPage />);

    // Custodian should NOT be redirected
    expect(mockPush).not.toHaveBeenCalledWith("/profile");

    // Custodian should see the SPARQL Explorer nav item
    expect(screen.getByText("SPARQL Explorer")).toBeInTheDocument();
  });
});
