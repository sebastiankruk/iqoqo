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

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import WorkLinksPage from "@/app/admin/work-links/page";
import { useProfile } from "@/lib/api/hooks";
import type { UserProfile } from "@/types/frbr";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/admin/work-links",
}));

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));

vi.mock("@/components/admin/work-link-reviewer", () => ({
  WorkLinkReviewer: ({ canEdit }: { canEdit: boolean }) => (
    <div data-testid="work-link-reviewer" data-can-edit={String(canEdit)} />
  ),
}));

describe("WorkLinksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders WorkLinkReviewer for custodian with write:metadata", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "custodian-1",
        email: "custodian@test.com",
        display_name: "Custodian",
        roles: ["contributor"],
        permissions: ["write:metadata", "read:metadata"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<WorkLinksPage />);
    expect(screen.getByTestId("work-link-reviewer")).toHaveAttribute("data-can-edit", "true");
  });

  it("redirects standard user lacking write:metadata to /profile", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "user-1",
        email: "user@test.com",
        display_name: "Reader",
        roles: ["user"],
        permissions: ["read:metadata"],
      } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<WorkLinksPage />);
    expect(mockPush).toHaveBeenCalledWith("/profile");
  });
});
