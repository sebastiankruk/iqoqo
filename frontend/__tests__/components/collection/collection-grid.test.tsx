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
 * Tests for the CollectionGrid component.
 */
import { render, screen } from "@testing-library/react";
import { beforeAll, describe, it, expect, vi } from "vitest";
import type { Item } from "@/types/frbr";
import { CollectionGrid } from "@/components/collection/collection-grid";

class MockIntersectionObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

beforeAll(() => {
  window.IntersectionObserver = MockIntersectionObserver as unknown as typeof IntersectionObserver;
});

/**
 * Helper to make a mock Item.
 *
 * @param id - Item ID.
 * @param title - Item title.
 * @param author - Author name.
 * @param manifestation_id - Optional manifestation ID.
 * @returns Fully populated Item mock object.
 */
function makeItem(id: number, title: string, author: string, manifestation_id: number = id): Item {
  return {
    id,
    manifestation_id,
    owner_id: "user1",
    status: "want_to_read",
    collection_status: "available",
    meta: {},
    title,
    authors: [author],
  };
}

describe("CollectionGrid", () => {
  it("shows an empty-state heading when the items array is empty", () => {
    render(<CollectionGrid items={[]} />);
    expect(screen.getByText("No items found")).toBeInTheDocument();
  });

  it("renders a helpful text in the empty state", () => {
    render(<CollectionGrid items={[]} />);
    expect(screen.getByText(/try adjusting your filters/i)).toBeInTheDocument();
  });

  it("renders one card per item", () => {
    const items = [
      makeItem(1, "Dune", "Frank Herbert"),
      makeItem(2, "Recursion", "Blake Crouch"),
      makeItem(3, "Project Hail Mary", "Andy Weir"),
    ];
    render(<CollectionGrid items={items} />);
    expect(screen.getAllByText("Dune").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Recursion").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Project Hail Mary").length).toBeGreaterThan(0);
  });

  it("groups identical manifestations into a single card", () => {
    const items = [
      makeItem(1, "Dune (Copy 1)", "Frank Herbert", 100),
      makeItem(2, "Dune (Copy 2)", "Frank Herbert", 100),
      makeItem(3, "Dune Messiah", "Frank Herbert", 101),
    ];
    render(<CollectionGrid items={items} />);

    expect(screen.getAllByText("Dune (Copy 1)").length).toBeGreaterThan(0);
    expect(screen.queryByText("Dune (Copy 2)")).not.toBeInTheDocument();
    expect(screen.getAllByText("Dune Messiah").length).toBeGreaterThan(0);
  });

  it("does not group items when isManifestationView is true", () => {
    const items = [
      makeItem(1, "Dune (Edition A)", "Frank Herbert", 100),
      makeItem(2, "Dune (Edition B)", "Frank Herbert", 100),
    ];
    render(<CollectionGrid items={items} isManifestationView={true} />);
    expect(screen.getAllByText("Dune (Edition A)").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Dune (Edition B)").length).toBeGreaterThan(0);
  });

  it("does not show the empty-state when items are present", () => {
    const items = [makeItem(1, "Dune", "Frank Herbert")];
    render(<CollectionGrid items={items} />);
    expect(screen.queryByText("No items found")).not.toBeInTheDocument();
  });

  it("creates links with correct item hrefs", () => {
    const items = [makeItem(7, "Neuromancer", "William Gibson")];
    render(<CollectionGrid items={items} />);
    const links = screen.getAllByRole("link");
    expect(links[0]).toHaveAttribute("href", "/item?id=7");
  });

  describe("Lazy Loading / Infinite Scroll", () => {
    it("renders a loading spinner at the bottom when isLoadingMore is true", () => {
      const items = [makeItem(1, "LazyTitle1", "Frank Herbert")];
      const { container } = render(<CollectionGrid items={items} hasMore={true} isLoadingMore={true} />);

      expect(screen.getAllByText("LazyTitle1").length).toBeGreaterThan(0);
      expect(container.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("does not show the 'No items found' empty state if it is currently loading the first page", () => {
      const { container } = render(<CollectionGrid items={[]} isLoadingMore={true} hasMore={true} />);

      expect(screen.queryByText("No items found")).not.toBeInTheDocument();
      expect(container.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("renders the scroll trigger area when hasMore is true and not loading", () => {
      const items = [makeItem(1, "LazyTitle3", "Frank Herbert")];
      const { container } = render(<CollectionGrid items={items} hasMore={true} isLoadingMore={false} />);

      expect(document.querySelector(".animate-spin")).not.toBeInTheDocument();
      const triggerDiv = container.querySelector(".h-6");
      expect(triggerDiv).toBeInTheDocument();
    });

    it("does not render the scroll trigger when hasMore is false", () => {
      const items = [makeItem(1, "LazyTitle4", "Frank Herbert")];
      const { container } = render(<CollectionGrid items={items} hasMore={false} isLoadingMore={false} />);

      const outerDiv = container.firstChild as HTMLElement;
      expect(outerDiv.children.length).toBe(1);
    });
  });
});
