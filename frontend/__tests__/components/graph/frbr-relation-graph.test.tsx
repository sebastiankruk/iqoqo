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
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FRBRRelationGraph } from "@/components/graph/frbr-relation-graph";
import type { CatalogGraphData } from "@/types/frbr";

describe("FRBRRelationGraph depth 3-4 & library layout (C140)", () => {
  it("places hop 3 and hop 4 nodes on non-origin radial coordinates", () => {
    const graph: CatalogGraphData = {
      anchor: { entity_type: "work", entity_id: 1, node_id: "work:1" },
      mode: "neighborhood",
      nodes: [
        { id: "work:1", entity_type: "work", entity_id: 1, label: "Root", hop: 0, is_anchor: true },
        { id: "expression:2", entity_type: "expression", entity_id: 2, label: "Exp", hop: 1, is_anchor: false },
        { id: "manifestation:3", entity_type: "manifestation", entity_id: 3, label: "Man", hop: 2, is_anchor: false },
        { id: "item:4", entity_type: "item", entity_id: 4, label: "Copy", hop: 3, is_anchor: false },
        { id: "lod:5", entity_type: "lod", entity_id: 5, label: "DBpedia", hop: 4, is_anchor: false },
      ],
      edges: [
        {
          id: "e1",
          source: "expression:2",
          target: "work:1",
          relation: "realizes",
          category: "frbr",
          label: "realizes",
        },
        {
          id: "e2",
          source: "manifestation:3",
          target: "expression:2",
          relation: "embodies",
          category: "frbr",
          label: "embodies",
        },
        {
          id: "e3",
          source: "item:4",
          target: "manifestation:3",
          relation: "exemplifies",
          category: "frbr",
          label: "exemplifies",
        },
        { id: "e4", source: "item:4", target: "lod:5", relation: "same_as", category: "lod", label: "sameAs" },
      ],
      meta: {
        depth: 4,
        requested_depth: 4,
        max_nodes: 150,
        max_edges: 400,
        node_count: 5,
        edge_count: 4,
        truncated: false,
      },
    };

    render(<FRBRRelationGraph graph={graph} onRecenter={vi.fn()} />);

    const hop3 = screen.getByTestId("graph-node-item:4").getAttribute("transform");
    const hop4 = screen.getByTestId("graph-node-lod:5").getAttribute("transform");
    expect(hop3).not.toBe("translate(0 0)");
    expect(hop4).not.toBe("translate(0 0)");
    expect(hop3).not.toBe(hop4);
  });

  it("renders canonical lod:<sha256> node shared across Contributor and multiple Works (C164)", () => {
    const canonId = "lod:9e107d9d372bb682";
    const graph: CatalogGraphData = {
      anchor: { entity_type: "contributor", entity_id: 7, node_id: "contributor:7" },
      mode: "neighborhood",
      nodes: [
        {
          id: "contributor:7",
          entity_type: "contributor",
          entity_id: 7,
          label: "Stephen King",
          hop: 0,
          is_anchor: true,
        },
        { id: "work:11", entity_type: "work", entity_id: 11, label: "It", hop: 1, is_anchor: false },
        {
          id: canonId,
          entity_type: "lod",
          entity_id: 101,
          label: "Stephen King",
          external_uri: "https://dbpedia.org/resource/Stephen_King",
          hop: 1,
          is_anchor: false,
        },
      ],
      edges: [
        {
          id: "w11--c7",
          source: "work:11",
          target: "contributor:7",
          relation: "contributed_by",
          category: "contributors",
          label: "author",
        },
        {
          id: "c7--lod",
          source: "contributor:7",
          target: canonId,
          relation: "same_as",
          category: "lod",
          label: "sameAs",
        },
        { id: "w11--lod", source: "work:11", target: canonId, relation: "same_as", category: "lod", label: "sameAs" },
      ],
      meta: {
        depth: 2,
        requested_depth: 2,
        max_nodes: 150,
        max_edges: 400,
        node_count: 3,
        edge_count: 3,
        truncated: false,
      },
    };

    render(<FRBRRelationGraph graph={graph} onRecenter={vi.fn()} />);

    const lodNodes = screen.getAllByTestId(`graph-node-${canonId}`);
    expect(lodNodes).toHaveLength(1);
    expect(screen.getAllByText("Stephen King").length).toBeGreaterThanOrEqual(2);
  });

  it("renders isolated nodes in unanchored library mode without collapsing onto (0,0)", () => {
    const libraryGraph: CatalogGraphData = {
      anchor: null,
      mode: "library",
      nodes: [
        { id: "work:10", entity_type: "work", entity_id: 10, label: "Isolated Work", hop: 0, is_anchor: false },
        {
          id: "contributor:20",
          entity_type: "contributor",
          entity_id: 20,
          label: "Isolated Author",
          hop: 0,
          is_anchor: false,
        },
      ],
      edges: [],
      meta: {
        depth: 0,
        requested_depth: 0,
        max_nodes: 150,
        max_edges: 400,
        node_count: 2,
        edge_count: 0,
        truncated: false,
      },
    };

    render(<FRBRRelationGraph graph={libraryGraph} onRecenter={vi.fn()} />);
    const n1 = screen.getByTestId("graph-node-work:10");
    const n2 = screen.getByTestId("graph-node-contributor:20");
    expect(n1).toBeInTheDocument();
    expect(n2).toBeInTheDocument();
    expect(n1.getAttribute("transform")).not.toBe(n2.getAttribute("transform"));
  });
});
