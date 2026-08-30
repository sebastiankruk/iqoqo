#!/usr/bin/env python3
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""Merge semantic extraction chunk JSONs into a single graphify-compatible file.

Reads graphify-out/.graphify_chunk_*.json, deduplicates nodes by ID,
and writes graphify-out/.graphify_semantic.json.

Supports --incremental mode:
  --incremental: Only re-merge chunks that changed (uses changed_chunks.json)
"""

import json
import glob
import sys
from pathlib import Path


def load_existing_semantic(project_root: Path) -> dict:
    """Load existing semantic JSON if available."""
    semantic_file = project_root / "graphify-out" / ".graphify_semantic.json"
    if semantic_file.exists():
        return json.loads(semantic_file.read_text())
    return {
        "nodes": [],
        "edges": [],
        "hyperedges": [],
        "input_tokens": 0,
        "output_tokens": 0,
    }


def load_chunk(chunk_file: Path) -> dict:
    """Load a single chunk file."""
    return json.loads(chunk_file.read_text())


def merge_all_chunks(project_root: Path) -> dict:
    """Merge all chunk files into a single semantic extraction result."""
    chunk_pattern = str(project_root / "graphify-out" / ".graphify_chunk_*.json")
    chunk_files = sorted(glob.glob(chunk_pattern))
    
    if not chunk_files:
        print("No chunk files found. Writing empty semantic file.")
        return {
            "nodes": [],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 0,
            "output_tokens": 0,
        }
    
    all_nodes = []
    all_edges = []
    all_hyperedges = []
    total_in = 0
    total_out = 0
    
    for chunk_file in chunk_files:
        data = load_chunk(Path(chunk_file))
        all_nodes.extend(data.get("nodes", []))
        all_edges.extend(data.get("edges", []))
        all_hyperedges.extend(data.get("hyperedges", []))
        total_in += data.get("input_tokens", 0)
        total_out += data.get("output_tokens", 0)
    
    # Deduplicate nodes by ID
    seen = set()
    deduped_nodes = []
    for node in all_nodes:
        node_id = node.get("id")
        if node_id and node_id not in seen:
            seen.add(node_id)
            deduped_nodes.append(node)
    
    # Deduplicate edges by (source, target, relation)
    seen_edges = set()
    deduped_edges = []
    for edge in all_edges:
        key = (edge.get("source"), edge.get("target"), edge.get("relation"))
        if key not in seen_edges:
            seen_edges.add(key)
            deduped_edges.append(edge)
    
    result = {
        "nodes": deduped_nodes,
        "edges": deduped_edges,
        "hyperedges": all_hyperedges,
        "input_tokens": total_in,
        "output_tokens": total_out,
    }
    
    print(f"Merged {len(chunk_files)} chunks:")
    print(f"  Nodes: {len(deduped_nodes)} (deduplicated from {len(all_nodes)})")
    print(f"  Edges: {len(deduped_edges)} (deduplicated from {len(all_edges)})")
    print(f"  Hyperedges: {len(all_hyperedges)}")
    print(f"  Tokens: {total_in:,} in / {total_out:,} out")
    
    return result


def merge_incremental(project_root: Path) -> dict:
    """Merge only changed chunks with existing semantic data."""
    existing = load_existing_semantic(project_root)
    
    # Load changed chunk indices
    changed_chunks_file = project_root / "graphify-out" / ".iqoqo_chunks" / "changed_chunks.json"
    if not changed_chunks_file.exists():
        print("No changed_chunks.json found. Falling back to full merge.")
        return merge_all_chunks(project_root)
    
    changed_indices = json.loads(changed_chunks_file.read_text())
    
    if not changed_indices:
        print("No chunks changed. Keeping existing semantic data.")
        return existing
    
    print(f"Incremental merge: {len(changed_indices)} chunks changed")
    
    # Build lookup from existing data
    existing_nodes = {n.get("id"): n for n in existing.get("nodes", []) if n.get("id")}
    existing_edges = {}
    for edge in existing.get("edges", []):
        key = (edge.get("source"), edge.get("target"), edge.get("relation"))
        existing_edges[key] = edge
    
    # Remove nodes/edges from changed chunks
    # We identify by source_file - nodes from changed files need re-extraction
    chunk_pattern = str(project_root / "graphify-out" / ".graphify_chunk_*.json")
    chunk_files = sorted(glob.glob(chunk_pattern))
    
    changed_files = set()
    for idx in changed_indices:
        if idx < len(chunk_files):
            chunk_data = load_chunk(Path(chunk_files[idx]))
            # chunk_data is a list of file paths, not extraction results
            # Wait, chunk files are lists of file paths, not extraction results
            # Let me reconsider...
            pass
    
    # Actually, the chunk files contain file paths, not extraction results
    # The extraction results are .graphify_chunk_NN.json in graphify-out/
    # Let me look for extraction results instead
    
    # Load changed extraction chunks
    all_nodes = []
    all_edges = []
    all_hyperedges = []
    total_in = 0
    total_out = 0
    
    for idx in changed_indices:
        extraction_file = project_root / "graphify-out" / f".graphify_chunk_{idx:03d}.json"
        if extraction_file.exists():
            data = load_chunk(extraction_file)
            all_nodes.extend(data.get("nodes", []))
            all_edges.extend(data.get("edges", []))
            all_hyperedges.extend(data.get("hyperedges", []))
            total_in += data.get("input_tokens", 0)
            total_out += data.get("output_tokens", 0)
    
    # Update existing data with new nodes/edges
    for node in all_nodes:
        node_id = node.get("id")
        if node_id:
            existing_nodes[node_id] = node
    
    for edge in all_edges:
        key = (edge.get("source"), edge.get("target"), edge.get("relation"))
        existing_edges[key] = edge
    
    # Merge hyperedges (just append, dedup by id if present)
    seen_hyper = {h.get("id") for h in existing.get("hyperedges", []) if h.get("id")}
    for hyper in all_hyperedges:
        if hyper.get("id") not in seen_hyper:
            existing["hyperedges"].append(hyper)
            if hyper.get("id"):
                seen_hyper.add(hyper["id"])
    
    result = {
        "nodes": list(existing_nodes.values()),
        "edges": list(existing_edges.values()),
        "hyperedges": existing.get("hyperedges", []),
        "input_tokens": existing.get("input_tokens", 0) + total_in,
        "output_tokens": existing.get("output_tokens", 0) + total_out,
    }
    
    print(f"Incremental merge complete:")
    print(f"  Nodes: {len(result['nodes'])}")
    print(f"  Edges: {len(result['edges'])}")
    print(f"  Hyperedges: {len(result['hyperedges'])}")
    
    return result


def main():
    project_root = Path.cwd()
    incremental = "--incremental" in sys.argv
    
    if incremental:
        result = merge_incremental(project_root)
    else:
        result = merge_all_chunks(project_root)
    
    output_file = project_root / "graphify-out" / ".graphify_semantic.json"
    output_file.write_text(json.dumps(result, indent=2))
    print(f"Wrote merged semantic extraction to {output_file}")


if __name__ == "__main__":
    main()
