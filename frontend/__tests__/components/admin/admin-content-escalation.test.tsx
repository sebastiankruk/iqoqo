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
import { describe, it, expect, vi, beforeEach } from "vitest";

import ContentManagementPage from "@/app/admin/content/page";
import { useProfile } from "@/lib/api/hooks";

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
  useRegenerateCover: vi.fn(() => ({ mutateAsync: vi.fn() })),
  queryKeys: { manifestation: vi.fn(), item: vi.fn() },
  useAppConfig: vi.fn(() => ({ data: { maintenance_mode: false }, isLoading: false })),
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/admin/content"),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
  useSearchParams: vi.fn(() => new URLSearchParams("tab=profile")),
}));

vi.mock("@/components/admin/escalation-queue", () => ({
  EscalationQueue: () => <div data-testid="escalation-queue">Queue</div>,
}));

vi.mock("@/components/admin/instance-settings", () => ({
  InstanceSettings: () => <div data-testid="instance-settings" />,
}));

vi.mock("@/components/admin/user-management", () => ({
  UserManagement: () => <div data-testid="user-management" />,
}));

vi.mock("@/components/admin/frbr-editor", () => ({
  FrbrEditor: () => <div data-testid="frbr-editor" />,
}));

vi.mock("@/components/admin/cover-editor/cover-art-editor-wrapper", () => ({
  CoverArtEditorWrapper: () => <div data-testid="cover-art-editor" />,
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <div data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <div data-testid="footer" />,
}));

describe("Admin Content Page - Escalation Queue tab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Escalation Queue nav item for custodian with escalate:resolve", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "custodian-id",
        email: "custodian@test.local",
        permissions: ["escalate:resolve"],
      },
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<ContentManagementPage />);

    expect(screen.getByText("Escalation Queue")).toBeInTheDocument();
  });

  it("hides Escalation Queue nav item for regular user without escalate:resolve", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: "user-id",
        email: "user@test.local",
        permissions: ["read:metadata"],
      },
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    render(<ContentManagementPage />);

    expect(screen.queryByText("Escalation Queue")).not.toBeInTheDocument();
  });

  it("hides Escalation Queue for unauthenticated (loading state)", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as unknown as ReturnType<typeof useProfile>);

    render(<ContentManagementPage />);

    expect(screen.queryByText("Escalation Queue")).not.toBeInTheDocument();
  });
});
