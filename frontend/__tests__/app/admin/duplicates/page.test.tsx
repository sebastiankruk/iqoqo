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
import DuplicatesPage from "@/app/admin/duplicates/page";
import { useProfile } from "@/lib/api/hooks";
import { useRouter } from "next/navigation";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { UserProfile } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: vi.fn(),
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <div data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <div data-testid="footer" />,
}));

vi.mock("@/components/admin/duplicate-reviewer", () => ({
  DuplicateReviewer: ({ canEdit }: { canEdit: boolean }) => (
    <div data-testid="duplicate-reviewer" data-can-edit={String(canEdit)} />
  ),
}));

/**
 * Build a profile payload for a given role and permission set.
 *
 * @param roles - Role names to attach to the profile.
 * @param permissions - Colon-format permission strings, as the API returns them.
 * @returns A profile object shaped for `useProfile`.
 */
function profile(roles: string[], permissions: string[]): UserProfile {
  return {
    id: "1",
    email: "user@test.com",
    display_name: "Test User",
    roles,
    permissions,
  } as unknown as UserProfile;
}

describe("DuplicatesPage", () => {
  const mockPush = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({ push: mockPush } as unknown as ReturnType<typeof useRouter>);
  });

  /**
   * Install a resolved profile for the next render.
   *
   * @param data - The profile `useProfile` should return.
   */
  function mockProfile(data: UserProfile): void {
    vi.mocked(useProfile).mockReturnValue({ data, isLoading: false } as unknown as ReturnType<typeof useProfile>);
  }

  it("shows a loading state initially", () => {
    vi.mocked(useProfile).mockReturnValue({ data: undefined, isLoading: true } as unknown as ReturnType<
      typeof useProfile
    >);

    render(<DuplicatesPage />);

    expect(screen.queryByTestId("duplicate-reviewer")).not.toBeInTheDocument();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("redirects an unauthenticated visitor to /login", () => {
    vi.mocked(useProfile).mockReturnValue({ data: undefined, isLoading: false } as unknown as ReturnType<
      typeof useProfile
    >);

    render(<DuplicatesPage />);

    expect(mockPush).toHaveBeenCalledWith("/login");
  });

  // Regression: the page previously had no access guard at all, so any
  // authenticated user could load it and only discovered the refusal when the
  // queue request came back 403.
  it("redirects a user without write:metadata to /profile", () => {
    mockProfile(profile(["user"], ["read:metadata", "write:item"]));

    render(<DuplicatesPage />);

    expect(mockPush).toHaveBeenCalledWith("/profile");
    expect(screen.queryByTestId("duplicate-reviewer")).not.toBeInTheDocument();
  });

  it("lets a custodian with write:metadata review duplicates", () => {
    mockProfile(profile(["contributor"], ["read:metadata", "write:metadata"]));

    render(<DuplicatesPage />);

    expect(mockPush).not.toHaveBeenCalled();
    const reviewer = screen.getByTestId("duplicate-reviewer");
    expect(reviewer).toBeInTheDocument();
    // Custodians get the full workflow, matching the write:metadata API gate.
    expect(reviewer).toHaveAttribute("data-can-edit", "true");
  });

  it("lets an admin review duplicates", () => {
    mockProfile(profile(["admin"], ["read:metadata", "write:metadata"]));

    render(<DuplicatesPage />);

    expect(mockPush).not.toHaveBeenCalled();
    expect(screen.getByTestId("duplicate-reviewer")).toBeInTheDocument();
  });

  // Regression: the sidebar entry was gated on read:metadata, which the standard
  // user role also holds, so every logged-in user saw a Duplicate Review link in
  // their Custodians menu that led to a 403.
  it("hides the Duplicate Review nav link from a read-only metadata user", () => {
    mockProfile(profile(["user"], ["read:metadata"]));

    render(<DuplicatesPage />);

    expect(screen.queryByRole("link", { name: "Duplicate Review" })).not.toBeInTheDocument();
  });

  it("shows the Duplicate Review nav link to a custodian", () => {
    mockProfile(profile(["contributor"], ["read:metadata", "write:metadata"]));

    render(<DuplicatesPage />);

    expect(screen.getByRole("link", { name: "Duplicate Review" })).toHaveAttribute("href", "/admin/duplicates");
  });
});
