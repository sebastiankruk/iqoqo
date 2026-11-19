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
"use client";

import React, { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  Compass,
  ExternalLink,
  GitBranch,
  MapPin,
  RotateCcw,
  Search,
  Sparkles,
  User,
  ZoomIn,
  ZoomOut,
  BookOpen,
  Layers,
  Package,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type {
  CatalogGraphData,
  GraphAnchorEntityType,
  GraphEdgeCategory,
  GraphNode,
  GraphNodeEntityType,
} from "@/types/frbr";

interface Point {
  x: number;
  y: number;
}

const ALL_EDGE_CATEGORIES: GraphEdgeCategory[] = ["frbr", "series", "parts_expansions", "contributors", "maps", "lod"];

const RECENTERABLE_TYPES = new Set<GraphNodeEntityType>(["work", "expression", "manifestation", "item"]);

const NODE_STYLE_MAP: Record<
  GraphNodeEntityType,
  { fill: string; stroke: string; badgeClass: string; Icon: React.ComponentType<{ className?: string }> }
> = {
  work: {
    fill: "#eef2ff",
    stroke: "#4f46e5",
    badgeClass: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border-indigo-500/30",
    Icon: BookOpen,
  },
  expression: {
    fill: "#e0f2fe",
    stroke: "#0284c7",
    badgeClass: "bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-500/30",
    Icon: Layers,
  },
  manifestation: {
    fill: "#d1fae5",
    stroke: "#059669",
    badgeClass: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
    Icon: Package,
  },
  item: {
    fill: "#f3e8ff",
    stroke: "#7c3aed",
    badgeClass: "bg-violet-500/15 text-violet-700 dark:text-violet-300 border-violet-500/30",
    Icon: Sparkles,
  },
  contributor: {
    fill: "#ffe4e6",
    stroke: "#e11d48",
    badgeClass: "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30",
    Icon: User,
  },
  map: {
    fill: "#ccfbf1",
    stroke: "#0d9488",
    badgeClass: "bg-teal-500/15 text-teal-700 dark:text-teal-300 border-teal-500/30",
    Icon: MapPin,
  },
  lod: {
    fill: "#ffedd5",
    stroke: "#ea580c",
    badgeClass: "bg-orange-500/15 text-orange-700 dark:text-orange-300 border-orange-500/30",
    Icon: GitBranch,
  },
};

/** Return true when a candidate external URL uses http(s) protocol. */
function isSafeExternalUrl(raw?: string | null): boolean {
  if (!raw) return false;
  try {
    const parsed = new URL(raw);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

/** Truncate node labels cleanly for compact SVG presentation. */
function truncateLabel(text: string, maxLen = 22): string {
  if (text.length <= maxLen) return text;
  return `${text.slice(0, maxLen - 1)}…`;
}

/** Compute deterministic concentric radial coordinates around the anchor node. */
function computeRadialLayout(nodes: GraphNode[]): Record<string, Point> {
  const positions: Record<string, Point> = {};
  const byHop = new Map<number, GraphNode[]>();

  for (const node of nodes) {
    const bucket = byHop.get(node.hop) ?? [];
    bucket.push(node);
    byHop.set(node.hop, bucket);
  }

  for (const node of byHop.get(0) ?? []) {
    positions[node.id] = { x: 0, y: 0 };
  }

  const hop1 = byHop.get(1) ?? [];
  hop1.forEach((node, idx) => {
    const angle = (2 * Math.PI * idx) / Math.max(hop1.length, 1) - Math.PI / 2;
    const radius = hop1.length > 12 ? (idx % 2 === 0 ? 210 : 295) : 235;
    positions[node.id] = {
      x: Math.round(Math.cos(angle) * radius),
      y: Math.round(Math.sin(angle) * radius),
    };
  });

  const hop2 = byHop.get(2) ?? [];
  hop2.forEach((node, idx) => {
    const angle = (2 * Math.PI * idx) / Math.max(hop2.length, 1) - Math.PI / 3;
    const radius = hop2.length > 18 ? (idx % 2 === 0 ? 415 : 510) : 445;
    positions[node.id] = {
      x: Math.round(Math.cos(angle) * radius),
      y: Math.round(Math.sin(angle) * radius),
    };
  });

  return positions;
}

export interface FRBRRelationGraphProps {
  graph: CatalogGraphData;
  onRecenter: (entityType: GraphAnchorEntityType, entityId: number) => void;
}

/**
 * Interactive SVG neighborhood explorer for FRBR hierarchies, Series,
 * WorkParts, Expansions, Contributors, Maps, and accepted LOD links.
 */
export function FRBRRelationGraph({ graph, onRecenter }: FRBRRelationGraphProps) {
  const t = useTranslations("graph");

  const [enabledCategories, setEnabledCategories] = useState<Set<GraphEdgeCategory>>(
    () => new Set(ALL_EDGE_CATEGORIES)
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string>(graph.anchor.node_id);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<Point>({ x: 0, y: 0 });
  const [draggedPositions, setDraggedPositions] = useState<Record<string, Point>>({});

  const panDragRef = useRef<{ active: boolean; startX: number; startY: number; origX: number; origY: number } | null>(
    null
  );
  const nodeDragRef = useRef<{
    nodeId: string;
    startClientX: number;
    startClientY: number;
    origNodePos: Point;
  } | null>(null);

  const visibleEdges = useMemo(
    () => graph.edges.filter(edge => enabledCategories.has(edge.category)),
    [graph.edges, enabledCategories]
  );

  const visibleNodes = useMemo(() => {
    const connectedIds = new Set<string>([graph.anchor.node_id]);
    for (const edge of visibleEdges) {
      connectedIds.add(edge.source);
      connectedIds.add(edge.target);
    }
    return graph.nodes.filter(node => connectedIds.has(node.id));
  }, [graph.nodes, graph.anchor.node_id, visibleEdges]);

  const basePositions = useMemo(() => computeRadialLayout(visibleNodes), [visibleNodes]);

  const getNodePosition = (nodeId: string): Point =>
    draggedPositions[nodeId] ?? basePositions[nodeId] ?? { x: 0, y: 0 };

  const selectedNode = useMemo(
    () => visibleNodes.find(n => n.id === selectedNodeId) ?? visibleNodes.find(n => n.is_anchor) ?? null,
    [visibleNodes, selectedNodeId]
  );

  const nodeById = useMemo(() => {
    const map = new Map<string, GraphNode>();
    for (const node of visibleNodes) map.set(node.id, node);
    return map;
  }, [visibleNodes]);

  const selectedConnections = useMemo(() => {
    if (!selectedNode) return [];
    return visibleEdges
      .filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
      .map(edge => {
        const peerId = edge.source === selectedNode.id ? edge.target : edge.source;
        return {
          edge,
          peer: nodeById.get(peerId) ?? null,
        };
      });
  }, [selectedNode, visibleEdges, nodeById]);

  const normalizedSearch = searchQuery.trim().toLowerCase();

  const toggleCategory = (cat: GraphEdgeCategory) => {
    setEnabledCategories(prev => {
      const next = new Set(prev);
      if (next.has(cat)) {
        next.delete(cat);
      } else {
        next.add(cat);
      }
      return next;
    });
  };

  const resetViewport = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setDraggedPositions({});
  };

  const handleSvgPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    if ((e.target as Element).closest("[data-graph-node]")) return;
    panDragRef.current = {
      active: true,
      startX: e.clientX,
      startY: e.clientY,
      origX: pan.x,
      origY: pan.y,
    };
  };

  const handleSvgPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (nodeDragRef.current) {
      const { nodeId, startClientX, startClientY, origNodePos } = nodeDragRef.current;
      const dx = (e.clientX - startClientX) / zoom;
      const dy = (e.clientY - startClientY) / zoom;
      setDraggedPositions(prev => ({
        ...prev,
        [nodeId]: { x: origNodePos.x + dx, y: origNodePos.y + dy },
      }));
      return;
    }
    if (panDragRef.current?.active) {
      const dx = e.clientX - panDragRef.current.startX;
      const dy = e.clientY - panDragRef.current.startY;
      setPan({ x: panDragRef.current.origX + dx, y: panDragRef.current.origY + dy });
    }
  };

  const handleSvgPointerUp = () => {
    panDragRef.current = null;
    nodeDragRef.current = null;
  };

  const handleWheel = (e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom(prev => Math.min(2.5, Math.max(0.35, Number((prev * factor).toFixed(2)))));
  };

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
      <div className="flex-1 flex flex-col gap-3 min-w-0">
        {/* Filter Bar & Viewport Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-card p-3">
          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Edge category filters">
            {ALL_EDGE_CATEGORIES.map(cat => {
              const active = enabledCategories.has(cat);
              return (
                <button
                  key={cat}
                  type="button"
                  data-testid={`graph-filter-${cat}`}
                  aria-pressed={active}
                  onClick={() => toggleCategory(cat)}
                  className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                    active
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-muted/40 text-muted-foreground border-border hover:bg-muted"
                  }`}
                >
                  {t(`categories.${cat}`)}
                </button>
              );
            })}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                type="search"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder={t("searchPlaceholder")}
                aria-label={t("searchPlaceholder")}
                className="h-8 w-44 rounded-md border border-input bg-background pl-8 pr-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={() => setZoom(z => Math.min(2.5, Number((z + 0.15).toFixed(2))))}
                aria-label={t("zoomIn")}
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </Button>
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={() => setZoom(z => Math.max(0.35, Number((z - 0.15).toFixed(2))))}
                aria-label={t("zoomOut")}
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </Button>
              <Button type="button" variant="outline" size="sm" className="h-8 gap-1 text-xs" onClick={resetViewport}>
                <RotateCcw className="h-3 w-3" />
                <span>{t("resetView")}</span>
              </Button>
            </div>
          </div>
        </div>

        {/* SVG Graph Canvas */}
        <div className="relative h-[560px] w-full overflow-hidden rounded-xl border border-border bg-muted/15 shadow-inner">
          <svg
            data-testid="frbr-relation-graph-svg"
            viewBox="-600 -340 1200 680"
            className="h-full w-full select-none touch-none cursor-grab active:cursor-grabbing"
            onPointerDown={handleSvgPointerDown}
            onPointerMove={handleSvgPointerMove}
            onPointerUp={handleSvgPointerUp}
            onPointerLeave={handleSvgPointerUp}
            onWheel={handleWheel}
          >
            <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
              {/* Edges */}
              {visibleEdges.map(edge => {
                const src = getNodePosition(edge.source);
                const dst = getNodePosition(edge.target);
                const midX = (src.x + dst.x) / 2;
                const midY = (src.y + dst.y) / 2;
                const isRelatedToSelected =
                  selectedNode && (edge.source === selectedNode.id || edge.target === selectedNode.id);
                return (
                  <g key={edge.id} opacity={isRelatedToSelected || !selectedNode ? 0.9 : 0.4}>
                    <line
                      x1={src.x}
                      y1={src.y}
                      x2={dst.x}
                      y2={dst.y}
                      stroke={isRelatedToSelected ? "currentColor" : "#94a3b8"}
                      strokeWidth={isRelatedToSelected ? 2.2 : 1.4}
                      strokeDasharray={edge.category === "lod" ? "4 3" : undefined}
                      className={isRelatedToSelected ? "text-primary" : ""}
                    />
                    <text
                      x={midX}
                      y={midY - 4}
                      textAnchor="middle"
                      className="fill-muted-foreground text-[9px] font-medium pointer-events-none"
                    >
                      {edge.label}
                    </text>
                  </g>
                );
              })}

              {/* Nodes */}
              {visibleNodes.map(node => {
                const pos = getNodePosition(node.id);
                const style = NODE_STYLE_MAP[node.entity_type] ?? NODE_STYLE_MAP.work;
                const isSelected = selectedNode?.id === node.id;
                const matchesSearch =
                  !normalizedSearch ||
                  node.label.toLowerCase().includes(normalizedSearch) ||
                  (node.subtitle || "").toLowerCase().includes(normalizedSearch);
                const radius = node.is_anchor ? 34 : 24;

                return (
                  <g
                    key={node.id}
                    data-graph-node="true"
                    data-testid={`graph-node-${node.id}`}
                    role="button"
                    tabIndex={0}
                    aria-label={`${t(`nodeTypes.${node.entity_type}`)}: ${node.label}`}
                    transform={`translate(${pos.x} ${pos.y})`}
                    opacity={matchesSearch ? 1 : 0.25}
                    className="cursor-pointer focus:outline-none"
                    onClick={() => setSelectedNodeId(node.id)}
                    onKeyDown={e => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setSelectedNodeId(node.id);
                      }
                    }}
                    onPointerDown={e => {
                      e.stopPropagation();
                      setSelectedNodeId(node.id);
                      nodeDragRef.current = {
                        nodeId: node.id,
                        startClientX: e.clientX,
                        startClientY: e.clientY,
                        origNodePos: getNodePosition(node.id),
                      };
                    }}
                  >
                    <circle
                      r={radius}
                      fill={style.fill}
                      stroke={style.stroke}
                      strokeWidth={isSelected ? 4 : node.is_anchor ? 3 : 2}
                    />
                    <text
                      y={3}
                      textAnchor="middle"
                      fill={style.stroke}
                      className="text-[10px] font-bold uppercase tracking-wider pointer-events-none"
                    >
                      {node.entity_type.slice(0, 4)}
                    </text>
                    <text
                      y={radius + 14}
                      textAnchor="middle"
                      className="fill-foreground text-[11px] font-semibold pointer-events-none"
                    >
                      {truncateLabel(node.label)}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        </div>
      </div>

      {/* Node Inspection Side Drawer */}
      <aside
        data-testid="graph-inspector-drawer"
        className="w-full lg:w-88 shrink-0 rounded-xl border border-border bg-card p-5 flex flex-col gap-4"
      >
        {selectedNode ? (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className={NODE_STYLE_MAP[selectedNode.entity_type]?.badgeClass ?? ""}>
                {t(`nodeTypes.${selectedNode.entity_type}`)}
              </Badge>
              {selectedNode.is_anchor && <Badge variant="secondary">{t("anchorBadge")}</Badge>}
              {selectedNode.visibility && (
                <Badge variant="outline" className="text-xs uppercase">
                  {selectedNode.visibility}
                </Badge>
              )}
              {selectedNode.work_kind && (
                <Badge variant="outline" className="text-xs uppercase">
                  {selectedNode.work_kind}
                </Badge>
              )}
            </div>

            <div>
              <h2 className="font-serif text-xl font-bold text-foreground break-words">{selectedNode.label}</h2>
              {selectedNode.subtitle && <p className="text-xs text-muted-foreground mt-1">{selectedNode.subtitle}</p>}
              {selectedNode.issn && (
                <p className="text-xs font-mono text-muted-foreground mt-1">ISSN {selectedNode.issn}</p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              {!selectedNode.is_anchor && RECENTERABLE_TYPES.has(selectedNode.entity_type) && (
                <Button
                  type="button"
                  variant="default"
                  size="sm"
                  data-testid="graph-recenter-button"
                  onClick={() =>
                    onRecenter(selectedNode.entity_type as GraphAnchorEntityType, Number(selectedNode.entity_id))
                  }
                  className="gap-1.5 justify-start"
                >
                  <Compass className="h-4 w-4" />
                  <span>{t("recenter")}</span>
                </Button>
              )}

              {selectedNode.entity_type === "lod" && isSafeExternalUrl(selectedNode.external_uri) ? (
                <Button asChild variant="outline" size="sm" className="gap-1.5 justify-start">
                  <a href={selectedNode.external_uri!} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-4 w-4" />
                    <span>{t("openExternal")}</span>
                  </a>
                </Button>
              ) : (
                selectedNode.url &&
                selectedNode.url.startsWith("/") && (
                  <Button asChild variant="outline" size="sm" className="gap-1.5 justify-start">
                    <Link href={selectedNode.url} data-testid="graph-open-entity-link">
                      <ExternalLink className="h-4 w-4" />
                      <span>{t("openEntity")}</span>
                    </Link>
                  </Button>
                )
              )}
            </div>

            <div className="border-t border-border pt-3 space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("connections")} ({selectedConnections.length})
              </h3>
              <ul className="max-h-60 overflow-y-auto space-y-1.5 pr-1">
                {selectedConnections.map(({ edge, peer }) => (
                  <li key={edge.id}>
                    <button
                      type="button"
                      onClick={() => peer && setSelectedNodeId(peer.id)}
                      className="w-full rounded-md border border-border/60 bg-background/60 px-2.5 py-2 text-left text-xs hover:bg-muted/50 transition-colors"
                    >
                      <div className="font-mono text-[10px] text-primary">{edge.label}</div>
                      <div className="font-medium text-foreground truncate">{peer ? peer.label : edge.target}</div>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">{t("selectPrompt")}</p>
        )}
      </aside>
    </div>
  );
}
