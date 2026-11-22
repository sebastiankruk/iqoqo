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
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import GraphPage from "@/app/graph/page";
import { ItemHeader } from "@/components/item/item-header";
import { WorkDetailClient } from "@/components/work/work-detail-client";
import { ExpressionDetailClient } from "@/components/expression/expression-detail-client";
import type { CatalogGraphData, ExpressionDetail, Item, WorkDetail } from "@/types/frbr";

const mockPush = vi.fn();
const mockSearchParams = new URLSearchParams("type=work&id=42&depth=2");

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => mockSearchParams,
  usePathname: () => "/graph",
  useParams: () => ({ id: "42" }),
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));

const mockUseCatalogGraph = vi.fn();
const mockUseCatalogLibraryGraph = vi.fn();

vi.mock("@/lib/api/hooks/catalog", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/hooks/catalog")>();
  return {
    ...actual,
    useCatalogGraph: (entityType: string, entityId: number, depth: number, enabled: boolean) =>
      mockUseCatalogGraph(entityType, entityId, depth, enabled),
    useCatalogLibraryGraph: (entityTypes?: string, edgeTypes?: string, enabled?: boolean) =>
      mockUseCatalogLibraryGraph(entityTypes, edgeTypes, enabled),
  };
});

vi.mock("@/lib/api/hooks", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/hooks")>();
  return {
    ...actual,
    useWork: (_id: number, initial?: WorkDetail) => ({ data: initial, isLoading: false, isError: false }),
    useExpression: (_id: number, initial?: ExpressionDetail) => ({ data: initial, isLoading: false }),
    useWorkParts: () => ({ data: { data: [] } }),
    useProfile: () => ({ data: null }),
  };
});

vi.mock("@/lib/api/wishlist", () => ({
  useWishlist: () => ({ data: [] }),
  useCreateWishlistItem: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteWishlistItem: () => ({ mutateAsync: vi.fn(), isPending: false }),
  wishlistQueryKeys: { all: ["wishlist"] },
}));

vi.mock("@tanstack/react-query", async importOriginal => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  };
});

const SAMPLE_GRAPH: CatalogGraphData = {
  anchor: { entity_type: "work", entity_id: 42, node_id: "work:42" },
  nodes: [
    {
      id: "work:42",
      entity_type: "work",
      entity_id: 42,
      label: "The Hobbit",
      subtitle: "J.R.R. Tolkien",
      hop: 0,
      is_anchor: true,
      url: "/work/42",
    },
    {
      id: "expression:10",
      entity_type: "expression",
      entity_id: 10,
      label: "The Hobbit (en)",
      subtitle: "text • en",
      hop: 1,
      is_anchor: false,
      url: "/expression/10",
    },
    {
      id: "manifestation:88",
      entity_type: "manifestation",
      entity_id: 88,
      label: "The Hobbit 1937",
      subtitle: "hardcover • Allen & Unwin",
      hop: 2,
      is_anchor: false,
      url: "/manifestation/88",
    },
    {
      id: "contributor:5",
      entity_type: "contributor",
      entity_id: 5,
      label: "J.R.R. Tolkien",
      subtitle: "person",
      hop: 1,
      is_anchor: false,
      url: "/collection?q=J.R.R.%20Tolkien",
    },
    {
      id: "lod:9",
      entity_type: "lod",
      entity_id: 9,
      label: "DBpedia: The Hobbit",
      subtitle: "dbpedia",
      authority: "dbpedia",
      external_uri: "https://dbpedia.org/resource/The_Hobbit",
      hop: 1,
      is_anchor: false,
      url: "https://dbpedia.org/resource/The_Hobbit",
    },
  ],
  edges: [
    {
      id: "expression:10--realizes--work:42",
      source: "expression:10",
      target: "work:42",
      relation: "realizes",
      category: "frbr",
      label: "realizes",
    },
    {
      id: "manifestation:88--embodies--expression:10",
      source: "manifestation:88",
      target: "expression:10",
      relation: "embodies",
      category: "frbr",
      label: "embodies",
    },
    {
      id: "work:42--contributed_by--contributor:5",
      source: "work:42",
      target: "contributor:5",
      relation: "contributed_by",
      category: "contributors",
      label: "author",
    },
    {
      id: "work:42--same_as--lod:9",
      source: "work:42",
      target: "lod:9",
      relation: "same_as",
      category: "lod",
      label: "sameAs (dbpedia)",
    },
  ],
  meta: {
    depth: 2,
    requested_depth: 2,
    max_nodes: 150,
    node_count: 5,
    edge_count: 4,
    truncated: true,
  },
};

describe("FRBR Relation Graph Explorer (/graph) & Entry Buttons (C133)", () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockSearchParams.set("type", "work");
    mockSearchParams.set("id", "42");
    mockSearchParams.set("depth", "2");
    mockSearchParams.delete("mode");
    mockSearchParams.delete("entities");
    mockUseCatalogGraph.mockReturnValue({
      data: SAMPLE_GRAPH,
      isLoading: false,
      isError: false,
    });
    mockUseCatalogLibraryGraph.mockReturnValue({
      data: { ...SAMPLE_GRAPH, anchor: null, mode: "library" },
      isLoading: false,
      isError: false,
    });
  });

  it("renders nodes, truncation banner, edge filters, depth 1-4 controls, and node inspection recenter action", () => {
    render(<GraphPage />);

    expect(screen.getByTestId("frbr-relation-graph-svg")).toBeInTheDocument();
    expect(screen.getByTestId("graph-truncated-banner")).toBeInTheDocument();
    expect(screen.getByTestId("graph-node-work:42")).toBeInTheDocument();
    expect(screen.getByTestId("graph-node-manifestation:88")).toBeInTheDocument();
    expect(screen.getByTestId("graph-node-lod:9")).toBeInTheDocument();
    expect(screen.getByTestId("graph-depth-3")).toBeInTheDocument();
    expect(screen.getByTestId("graph-depth-4")).toBeInTheDocument();

    // Open compact filter popover and toggle LOD filter off -> hides lod:9 node
    fireEvent.click(screen.getByTestId("graph-filters-trigger"));
    fireEvent.click(screen.getByTestId("graph-filter-lod"));
    expect(screen.queryByTestId("graph-node-lod:9")).not.toBeInTheDocument();

    // Select manifestation:88 and click Recenter
    fireEvent.click(screen.getByTestId("graph-node-manifestation:88"));
    const drawer = screen.getByTestId("graph-inspector-drawer");
    expect(drawer).toHaveTextContent("The Hobbit 1937");
    expect(screen.getByTestId("graph-open-entity-link")).toHaveAttribute("href", "/manifestation/88");

    fireEvent.click(screen.getByTestId("graph-recenter-button"));
    expect(mockPush).toHaveBeenCalledWith("/graph?type=manifestation&id=88&depth=2");

    // Clicking depth 4 navigates to depth=4
    fireEvent.click(screen.getByTestId("graph-depth-4"));
    expect(mockPush).toHaveBeenCalledWith("/graph?type=work&id=42&depth=4");
  });

  it("opens full-library concept explorer when type/id params are absent", () => {
    mockSearchParams.delete("type");
    mockSearchParams.delete("id");

    render(<GraphPage />);
    expect(screen.getByTestId("frbr-relation-graph-svg")).toBeInTheDocument();
    expect(screen.getByTestId("graph-entity-work")).toBeInTheDocument();
    expect(screen.getByTestId("graph-entity-contributor")).toBeInTheDocument();
    expect(screen.getByTestId("graph-fit-view")).toBeInTheDocument();
  });

  it("renders Explore Graph links on Work, Expression, and Item views", () => {
    const work: WorkDetail = {
      id: 42,
      title: "The Hobbit",
      authors: ["J.R.R. Tolkien"],
      expressions: [],
    };
    const { unmount } = render(<WorkDetailClient workId={42} initialWork={work} />);
    expect(screen.getByTestId("explore-graph-link")).toHaveAttribute("href", "/graph?type=work&id=42");
    unmount();

    const expr: ExpressionDetail = {
      id: 10,
      work_id: 42,
      work_title: "The Hobbit",
      authors: ["J.R.R. Tolkien"],
      content_type: "text",
      language: "en",
      manifestations: [],
    };
    const exprRender = render(<ExpressionDetailClient expressionId={10} initialExpression={expr} />);
    expect(screen.getByTestId("explore-graph-link")).toHaveAttribute("href", "/graph?type=expression&id=10");
    exprRender.unmount();

    const item: Item = {
      id: 99,
      manifestation_id: 88,
      owner_id: "user-1",
      status: "read",
      collection_status: "available",
      is_hidden: false,
      title: "The Hobbit",
      authors: ["J.R.R. Tolkien"],
      meta: {},
      manifestation_meta: {},
    };
    render(<ItemHeader item={item} />);
    expect(screen.getByTestId("explore-graph-link")).toHaveAttribute("href", "/graph?type=item&id=99");
  });
});
