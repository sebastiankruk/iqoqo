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
import { describe, it, expect, vi } from "vitest";
import { ItemTabs } from "@/components/item/item-tabs";
import type { Item } from "@/types/frbr";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/api/hooks", () => ({
  useAppConfig: vi.fn(() => ({ data: {} })),
  useWorkParts: vi.fn(() => ({ data: { data: [] } })),
  useProfile: vi.fn(() => ({ data: { id: "1", role: "admin", permissions: ["edit:manifestation"] } })),
  useSemanticLinks: vi.fn(() => ({ data: { links: [] }, isLoading: false })),
  useTriggerRelink: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteSemanticLink: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useFeedbackReviews: vi.fn(() => ({ data: { data: { reviews: [] } }, isLoading: false })),
  useNotes: vi.fn(() => ({ data: { data: { notes: [] } }, isLoading: false })),
}));

vi.mock("@/components/manifestation/semantic-links", () => ({
  SemanticLinks: ({ manifestationId, canEdit }: { manifestationId: number; canEdit: boolean }) => (
    <div data-testid="mock-semantic-links" data-manifestation-id={manifestationId} data-can-edit={canEdit}>
      SemanticLinks Mock
    </div>
  ),
}));

describe("ItemTabs Component", () => {
  const baseItem: Item = {
    id: 10,
    title: "Test Item",
    manifestation_id: 2069,
    manifestation_meta: {},
    owner_id: "user-1",
    owner_name: "Test User",
    owner_count: 1,
    status: "unread",
    collection_status: "available",
    meta: {},
  };

  it("renders SemanticLinks component in Details tab when manifestation_id is present", () => {
    render(<ItemTabs item={baseItem} />);

    const lodElement = screen.getByTestId("mock-semantic-links");
    expect(lodElement).toBeInTheDocument();
    expect(lodElement).toHaveAttribute("data-manifestation-id", "2069");
    expect(lodElement).toHaveAttribute("data-can-edit", "true");
  });

  it("does not render SemanticLinks if manifestation_id is missing", () => {
    const itemWithoutManif: Item = {
      ...baseItem,
      manifestation_id: 0,
    };

    render(<ItemTabs item={itemWithoutManif} />);
    expect(screen.queryByTestId("mock-semantic-links")).not.toBeInTheDocument();
  });
});
