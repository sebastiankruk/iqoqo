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
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { useProfile } from "@/lib/api/hooks";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { UserProfile } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

/**
 * Build a profile payload with a full admin permission set.
 *
 * @param roles - Role names to attach.
 * @param permissions - Colon-format permission strings.
 * @returns A profile object shaped for `useProfile`.
 */
function profile(roles: string[], permissions: string[]): UserProfile {
  return {
    id: "1",
    email: "admin@test.com",
    display_name: "Admin",
    roles,
    permissions,
  } as unknown as UserProfile;
}

const ADMIN_PERMISSIONS = [
  "write:metadata",
  "read:metadata",
  "edit:cover",
  "escalate:resolve",
  "read:users",
  "write:users",
  "read:roles",
  "config:external_apis",
  "config:federation",
  "config:affiliate",
  "config:internal",
];

/** Every link the sidebar can render, in display order. */
const ALL_ITEMS = [
  "Metadata",
  "Duplicate Review",
  "Cover Art",
  "User Requests",
  "SPARQL Explorer",
  "LOD Reconciliation",
  "Settings",
  "Federation",
  "Monetization",
  "API Integrations",
  "Users",
  "Item Ownership",
  "Roles",
  "Security",
];

describe("AdminSidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Install a resolved profile for the next render.
   *
   * @param data - The profile `useProfile` should return.
   */
  function mockProfile(data: UserProfile): void {
    vi.mocked(useProfile).mockReturnValue({ data, isLoading: false } as unknown as ReturnType<typeof useProfile>);
  }

  /**
   * Find a sidebar item by label, whichever role it renders as.
   *
   * Items with an `href` render as links; tab-only items render as buttons.
   *
   * @param label - Visible item label.
   * @returns The matching element.
   */
  function item(label: string): HTMLElement {
    const byLink = screen.queryByRole("link", { name: label });
    if (byLink) return byLink;
    return screen.getByRole("button", { name: label });
  }

  /**
   * Whether an element carries the active-state class as a whole token.
   *
   * A substring check would be wrong: the inactive class list contains
   * `hover:bg-muted/50`, which includes "bg-muted" as a substring.
   *
   * @param element - Element to inspect.
   * @returns True when the element is styled active.
   */
  function isActive(element: HTMLElement): boolean {
    return (element.getAttribute("class") ?? "").split(/\s+/).includes("bg-muted");
  }

  // Regression: the sidebar was duplicated across four admin pages and the
  // copies had already drifted -- the groups and duplicates pages were missing
  // "User Requests" and "LOD Reconciliation", and called the API section
  // "API Keys" where the settings and content pages said "API Integrations".
  it("offers the same links as the full permission set allows", () => {
    mockProfile(profile(["admin"], ADMIN_PERMISSIONS));

    render(<AdminSidebar />);

    for (const label of ALL_ITEMS) {
      expect(item(label)).toBeInTheDocument();
    }
  });

  it("never renders the drifted 'API Keys' label", () => {
    mockProfile(profile(["admin"], ADMIN_PERMISSIONS));

    render(<AdminSidebar />);

    expect(screen.queryByText("API Keys")).not.toBeInTheDocument();
    expect(item("API Integrations")).toBeInTheDocument();
  });

  it("shows both escalation queue and LOD reconciliation links", () => {
    mockProfile(profile(["admin"], ADMIN_PERMISSIONS));

    render(<AdminSidebar />);

    expect(screen.getByRole("link", { name: "User Requests" })).toHaveAttribute(
      "href",
      "/admin/content?tab=escalations"
    );
    expect(screen.getByRole("link", { name: "LOD Reconciliation" })).toHaveAttribute("href", "/admin/lod");
  });

  it("links Duplicate Review to the review queue", () => {
    mockProfile(profile(["admin"], ADMIN_PERMISSIONS));

    render(<AdminSidebar />);

    expect(screen.getByRole("link", { name: "Duplicate Review" })).toHaveAttribute("href", "/admin/duplicates");
  });

  it("marks the page it is rendering on as active", () => {
    mockProfile(profile(["admin"], ADMIN_PERMISSIONS));

    render(<AdminSidebar activeTab="duplicates" />);

    expect(isActive(item("Duplicate Review"))).toBe(true);
    expect(isActive(item("Cover Art"))).toBe(false);
  });

  it("hides both sections from a user with no custodian or settings permission", () => {
    mockProfile(profile(["user"], ["read:item", "write:item"]));

    render(<AdminSidebar />);

    expect(screen.queryByText("Custodians")).not.toBeInTheDocument();
    expect(screen.queryByText("Administration")).not.toBeInTheDocument();
  });

  it("still shows the section to a read-only metadata user, who may use SPARQL", () => {
    // read:metadata grants SPARQL access, so the Custodians section is
    // legitimately visible -- but the review queue is gated on write:metadata.
    mockProfile(profile(["user"], ["read:metadata"]));

    render(<AdminSidebar />);

    expect(screen.getByText("Custodians")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "SPARQL Explorer" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Duplicate Review" })).not.toBeInTheDocument();
  });

  it("gates Duplicate Review on write:metadata, not read:metadata", () => {
    // Regression: the link was once gated on read:metadata, which every
    // standard user holds, so ordinary users saw a link that led to a 403.
    mockProfile(profile(["contributor"], ["read:metadata", "write:metadata"]));

    render(<AdminSidebar />);

    expect(screen.getByRole("link", { name: "Duplicate Review" })).toBeInTheDocument();
  });

  it("forwards tab changes to the hosting page", () => {
    mockProfile(profile(["admin"], ADMIN_PERMISSIONS));
    const onTabChange = vi.fn();

    render(<AdminSidebar activeTab="instance" onTabChange={onTabChange} />);

    item("Users").click();
    expect(onTabChange).toHaveBeenCalledWith("users");
  });

  it("does not require an onNavigate prop, mirroring the previous inline blocks", () => {
    // Link items navigate by href, so the shared component deliberately does
    // not expose a navigation callback that no caller passes.
    mockProfile(profile(["admin"], ADMIN_PERMISSIONS));

    expect(() => render(<AdminSidebar activeTab="roles" />)).not.toThrow();
    expect(isActive(item("Roles"))).toBe(true);
  });
});
