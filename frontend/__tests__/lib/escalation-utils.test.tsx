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

import { describe, it, expect } from "vitest";
import { getTargetHref, getAdminTargetHref, getTargetLabel } from "@/lib/escalation-utils";
import type { EscalationRequest } from "@/types/frbr";

/**
 * Helper to build mock EscalationRequest for testing.
 * @param overrides Partial EscalationRequest fields.
 * @returns EscalationRequest object.
 */
function makeEsc(overrides: Partial<EscalationRequest> = {}): EscalationRequest {
  return {
    id: 1,
    user_id: "user-1",
    field_name: "title",
    suggested_value: "Fixed",
    status: "pending",
    request_type: "correction",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("getTargetHref", () => {
  it("returns manifestation link when manifestation_id is set", () => {
    const esc = makeEsc({ manifestation_id: 42 });
    expect(getTargetHref(esc)).toBe("/manifestation/42");
  });

  it("returns work collection link when work_id is set", () => {
    const esc = makeEsc({ work_id: 7 });
    expect(getTargetHref(esc)).toBe("/collection?work_id=7");
  });

  it("returns item link when item_id is set", () => {
    const esc = makeEsc({ item_id: 99 });
    expect(getTargetHref(esc)).toBe("/item/99");
  });

  it("returns null when no target entity is set", () => {
    const esc = makeEsc({});
    expect(getTargetHref(esc)).toBeNull();
  });

  it("prioritises manifestation over work when both set", () => {
    const esc = makeEsc({ manifestation_id: 1, work_id: 2 });
    expect(getTargetHref(esc)).toBe("/manifestation/1");
  });
});

describe("getAdminTargetHref", () => {
  it("returns admin metadata editor link for manifestation", () => {
    const esc = makeEsc({ manifestation_id: 10 });
    expect(getAdminTargetHref(esc)).toBe("/admin/content?tab=metadata&manifestationId=10");
  });

  it("returns work collection link for work", () => {
    const esc = makeEsc({ work_id: 5 });
    expect(getAdminTargetHref(esc)).toBe("/collection?work_id=5");
  });

  it("returns item link for item", () => {
    const esc = makeEsc({ item_id: 33 });
    expect(getAdminTargetHref(esc)).toBe("/item/33");
  });

  it("returns null when no target entity is set", () => {
    const esc = makeEsc({});
    expect(getAdminTargetHref(esc)).toBeNull();
  });
});

describe("getTargetLabel", () => {
  it("returns Manifestation label", () => {
    const esc = makeEsc({ manifestation_id: 42 });
    expect(getTargetLabel(esc)).toBe("Manifestation #42");
  });

  it("returns Work label", () => {
    const esc = makeEsc({ work_id: 7 });
    expect(getTargetLabel(esc)).toBe("Work #7");
  });

  it("returns Expression label", () => {
    const esc = makeEsc({ expression_id: 3 });
    expect(getTargetLabel(esc)).toBe("Expression #3");
  });

  it("returns Item label", () => {
    const esc = makeEsc({ item_id: 99 });
    expect(getTargetLabel(esc)).toBe("Item #99");
  });

  it("shows deleted fallback when only target_type is present", () => {
    const esc = makeEsc({ target_type: "manifestation" });
    expect(getTargetLabel(esc)).toBe("Manifestation (deleted)");
  });

  it("shows generic deleted fallback when nothing is present", () => {
    const esc = makeEsc({});
    expect(getTargetLabel(esc)).toBe("FRBR Entity (deleted)");
  });
});
