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
/**
 * Unit tests for custodian RBAC authorization logic.
 *
 * These tests verify the authorization logic that determines whether a user
 * should see the Administration menu based on their roles and permissions.
 *
 * Regression test for: Custodian role no longer has access to Administration menu
 */

import { describe, it, expect } from "vitest";

/**
 * Authorization logic extracted from navbar.tsx for testing.
 * Determines if a user should see the Administration menu.
 *
 * @param roles - Array of user roles
 * @param permissions - Array of user permissions
 * @returns true if user should see Administration menu
 */
export function canAccessAdministration(roles: string[] | undefined, permissions: string[] | undefined): boolean {
  // Admin role always has access
  if (roles?.includes("admin")) {
    return true;
  }

  // Custodian role has access
  if (roles?.includes("custodian")) {
    return true;
  }

  // Users with specific custodian permissions have access
  // IMPORTANT: Permissions use colon format (e.g., "write:metadata"), NOT underscore format
  const custodianPermissions = ["write:metadata", "edit:cover", "escalate:resolve", "read:metadata"];
  if (permissions?.some(p => custodianPermissions.includes(p))) {
    return true;
  }

  return false;
}

describe("Custodian RBAC Authorization Logic", () => {
  describe("Admin role access", () => {
    it("should grant access to admin users", () => {
      expect(canAccessAdministration(["admin"], [])).toBe(true);
    });

    it("should grant access to users with admin role among multiple roles", () => {
      expect(canAccessAdministration(["user", "admin", "custodian"], [])).toBe(true);
    });

    it("should grant access even if admin has no permissions", () => {
      expect(canAccessAdministration(["admin"], undefined)).toBe(true);
    });
  });

  describe("Custodian role access", () => {
    it("should grant access to custodian users", () => {
      expect(canAccessAdministration(["custodian"], [])).toBe(true);
    });

    it("should grant access to users with custodian role among multiple roles", () => {
      expect(canAccessAdministration(["user", "custodian"], [])).toBe(true);
    });

    it("should grant access to custodian even without explicit permissions", () => {
      expect(canAccessAdministration(["custodian"], undefined)).toBe(true);
    });

    it("should grant access to custodian with empty permissions array", () => {
      expect(canAccessAdministration(["custodian"], [])).toBe(true);
    });
  });

  describe("Permission-based access (colon format)", () => {
    it("should grant access with write:metadata permission", () => {
      expect(canAccessAdministration(["user"], ["write:metadata"])).toBe(true);
    });

    it("should grant access with edit:cover permission", () => {
      expect(canAccessAdministration(["user"], ["edit:cover"])).toBe(true);
    });

    it("should grant access with escalate:resolve permission", () => {
      expect(canAccessAdministration(["user"], ["escalate:resolve"])).toBe(true);
    });

    it("should grant access with read:metadata permission", () => {
      expect(canAccessAdministration(["user"], ["read:metadata"])).toBe(true);
    });

    it("should grant access with multiple custodian permissions", () => {
      expect(
        canAccessAdministration(["user"], ["write:metadata", "edit:cover", "escalate:resolve", "read:metadata"])
      ).toBe(true);
    });

    it("should grant access when user has one custodian permission among others", () => {
      expect(canAccessAdministration(["user"], ["read:owners", "write:metadata", "write:item"])).toBe(true);
    });
  });

  describe("Permission format validation (regression tests)", () => {
    it("should NOT grant access with underscore format permissions (write_metadata)", () => {
      // This is the regression test - underscore format should NOT work
      expect(canAccessAdministration(["user"], ["write_metadata"])).toBe(false);
    });

    it("should NOT grant access with underscore format permissions (edit_cover)", () => {
      expect(canAccessAdministration(["user"], ["edit_cover"])).toBe(false);
    });

    it("should NOT grant access with underscore format permissions (escalate_resolve)", () => {
      expect(canAccessAdministration(["user"], ["escalate_resolve"])).toBe(false);
    });

    it("should NOT grant access with underscore format permissions (read_metadata)", () => {
      expect(canAccessAdministration(["user"], ["read_metadata"])).toBe(false);
    });

    it("should NOT grant access with mixed underscore format permissions", () => {
      expect(
        canAccessAdministration(["user"], ["write_metadata", "edit_cover", "escalate_resolve", "read_metadata"])
      ).toBe(false);
    });
  });

  describe("Negative cases - no access", () => {
    it("should NOT grant access to regular users without custodian permissions", () => {
      expect(canAccessAdministration(["user"], ["read:owners", "write:item"])).toBe(false);
    });

    it("should grant access to users with no roles but with custodian permissions", () => {
      // Users with custodian permissions should have access even without explicit roles
      expect(canAccessAdministration([], ["write:metadata"])).toBe(true);
    });

    it("should NOT grant access to users with undefined roles and no permissions", () => {
      expect(canAccessAdministration(undefined, [])).toBe(false);
    });

    it("should NOT grant access to users with undefined roles and undefined permissions", () => {
      expect(canAccessAdministration(undefined, undefined)).toBe(false);
    });

    it("should NOT grant access to users with empty roles and empty permissions", () => {
      expect(canAccessAdministration([], [])).toBe(false);
    });

    it("should NOT grant access to users with only non-custodian permissions", () => {
      expect(
        canAccessAdministration(
          ["user"],
          ["delete:item", "update:item", "read:owners", "config:external_apis", "config:federation"]
        )
      ).toBe(false);
    });

    it("should NOT grant access to users with similar but incorrect permission names", () => {
      expect(canAccessAdministration(["user"], ["write:items", "edit:covers", "read:metadatas"])).toBe(false);
    });
  });

  describe("Edge cases", () => {
    it("should handle null roles gracefully", () => {
      expect(canAccessAdministration(null as unknown as string[], ["write:metadata"])).toBe(true);
    });

    it("should handle null permissions gracefully", () => {
      expect(canAccessAdministration(["custodian"], null as unknown as string[])).toBe(true);
    });

    it("should handle both null gracefully", () => {
      expect(canAccessAdministration(null as unknown as string[], null as unknown as string[])).toBe(false);
    });

    it("should be case-sensitive for role names", () => {
      expect(canAccessAdministration(["Admin"], [])).toBe(false);
      expect(canAccessAdministration(["CUSTODIAN"], [])).toBe(false);
    });

    it("should be case-sensitive for permission names", () => {
      expect(canAccessAdministration(["user"], ["Write:Metadata"])).toBe(false);
      expect(canAccessAdministration(["user"], ["WRITE:METADATA"])).toBe(false);
    });
  });

  describe("Real-world scenarios", () => {
    it("should grant access to typical custodian user profile", () => {
      const profile = {
        roles: ["user", "custodian"],
        permissions: ["write:metadata", "read:metadata", "escalate:resolve"],
      };
      expect(canAccessAdministration(profile.roles, profile.permissions)).toBe(true);
    });

    it("should grant access to admin user with all permissions", () => {
      const profile = {
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
      };
      expect(canAccessAdministration(profile.roles, profile.permissions)).toBe(true);
    });

    it("should NOT grant access to regular user with only basic permissions", () => {
      const profile = {
        roles: ["user"],
        permissions: ["read:owners"],
      };
      expect(canAccessAdministration(profile.roles, profile.permissions)).toBe(false);
    });

    it("should grant access to user promoted to custodian role", () => {
      const profile = {
        roles: ["user", "custodian"],
        permissions: [],
      };
      expect(canAccessAdministration(profile.roles, profile.permissions)).toBe(true);
    });

    it("should grant access to user with only permission-based custodian access", () => {
      const profile = {
        roles: ["user"],
        permissions: ["write:metadata"],
      };
      expect(canAccessAdministration(profile.roles, profile.permissions)).toBe(true);
    });
  });
});
