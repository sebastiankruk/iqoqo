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
"""Extract entities and relationships from .context/ markdown files.

Reads chunk manifests from graphify-out/.iqoqo_chunks/ and extracts
entities/relationships from markdown files, writing results to
graphify-out/.graphify_chunk_NN.json.

Node ID format: lowercase repo-relative path with underscore separator
"""

import json
import re
import sys
from pathlib import Path


def normalize_id(text: str) -> str:
    """Normalize text to lowercase [a-z0-9_] node ID."""
    return re.sub(r"[^a-z0-9_]", "_", text.lower()).strip("_")


def extract_entities_from_file(file_path: str) -> dict:
    """Extract entities and relationships from a single markdown file."""
    try:
        text = Path(file_path).read_text()
    except Exception:
        return {"nodes": [], "edges": [], "source_file": file_path}

    nodes = []
    edges = []

    # Extract Step headings: ## Step X — ROLE (`ROLE_TYPE`) *[timestamp]*
    step_pattern = r"##\s+Step\s+\d+\s*—\s*([^(`]+)\s*\(\`([^`]+)`\"\s*\*\[\s*[^\]]+\s*\]"
    for match in re.finditer(step_pattern, text):
        step_label = match.group(1).strip()
        step_type = match.group(2) if match.group(2) else "step"
        node_id = normalize_id(f"{step_type}_{step_label}_{Path(file_path).name}")
        nodes.append(
            {
                "id": node_id,
                "label": step_label,
                "type": step_type,
                "source_file": file_path,
            }
        )

    # Extract USER_REQUEST blocks
    user_request_pattern = r"<USER_REQUEST>(.*?)</USER_REQUEST>"
    for match in re.finditer(user_request_pattern, text, re.DOTALL):
        request_text = match.group(1).strip()
        # Extract task references like "Task 2.1", "Task 2.2", etc.
        task_pattern = r"Task\s+(\d+\.\d+)"
        for task_match in re.finditer(task_pattern, request_text):
            task_num = task_match.group(1)
            task_id = normalize_id(f"task_{task_num}_{Path(file_path).stem}")
            nodes.append(
                {
                    "id": task_id,
                    "label": f"Task {task_num}",
                    "type": "task",
                    "source_file": file_path,
                }
            )
            # Link task to step if a step context exists
            step_match = re.search(r"##\s+Step\s+\d+", text[: match.start()])
            if step_match:
                edges.append(
                    {
                        "source": task_id,
                        "target": normalize_id(f"step_{Path(file_path).stem}"),
                        "relation": "part_of",
                        "source_file": file_path,
                    }
                )

    # Extract skill references from ADDITIONAL_METADATA
    metadata_pattern = r"<ADDITIONAL_METADATA>(.*?)</ADDITIONAL_METADATA>"
    for match in re.finditer(metadata_pattern, text, re.DOTALL):
        meta_text = match.group(1)
        # Extract skill names like "iqoqo-devops-sre-expert"
        skill_pattern = r"Skill[:\s]+#?\s*([a-z][a-z0-9_-]*)"
        for skill_match in re.finditer(skill_pattern, meta_text):
            skill_name = skill_match.group(1).replace("-", "_")
            skill_id = normalize_id(f"skill_{skill_name}")
            nodes.append(
                {
                    "id": skill_id,
                    "label": skill_name.replace("_", " "),
                    "type": "skill",
                    "source_file": file_path,
                }
            )
            edges.append(
                {
                    "source": skill_id,
                    "target": normalize_id(f"step_0_{Path(file_path).stem}"),
                    "relation": "invoked_by",
                    "source_file": file_path,
                }
            )

    # Extract file path references
    file_ref_pattern = r'/opt/pre\.iqoqo[^\s"]+'
    for match in re.finditer(file_ref_pattern, text):
        file_ref = match.group(0)
        # Extract a short label from the path
        label = Path(file_ref).name.replace(".py", "").replace(".md", "")
        node_id = normalize_id(f"file_{label}_{Path(file_path).stem}")
        # Avoid duplicate nodes for same file path
        already = any(n.get("id") == node_id for n in nodes)
        if not already:
            nodes.append(
                {
                    "id": node_id,
                    "label": label,
                    "type": "file",
                    "source_file": file_path,
                }
            )

    # Extract relation references (people, commands, etc.)
    rel_pattern = r"@\[([^\]]+)\]"
    for match in re.finditer(rel_pattern, text):
        rel_name = match.group(1)
        rel_id = normalize_id(f"entity_{rel_name}_{Path(file_path).stem}")
        nodes.append(
            {
                "id": rel_id,
                "label": rel_name,
                "type": "entity",
                "source_file": file_path,
            }
        )

    return {"nodes": nodes, "edges": edges, "source_file": file_path}


def main():
    project_root = Path.cwd()
    chunks_dir = project_root / "graphify-out" / ".iqoqo_chunks"
    output_dir = project_root / "graphify-out"

    # Read chunk manifests
    chunk_files = sorted(chunks_dir.glob("chunk_*.json"))
    if not chunk_files:
        print("No chunk manifests found. Run scan_context.py first.")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    for i, cf in enumerate(chunk_files):
        files = json.loads(cf.read_text())
        all_nodes = []
        all_edges = []

        for file_path in files:
            result = extract_entities_from_file(file_path)
            all_nodes.extend(result["nodes"])
            all_edges.extend(result["edges"])

        # Deduplicate nodes by ID
        seen_ids = set()
        deduped_nodes = []
        for node in all_nodes:
            node_id = node.get("id")
            if node_id and node_id not in seen_ids:
                seen_ids.add(node_id)
                deduped_nodes.append(node)

        # Deduplicate edges by (source, target, relation)
        seen_edges = set()
        deduped_edges = []
        for edge in all_edges:
            key = (edge.get("source"), edge.get("target"), edge.get("relation"))
            if key not in seen_edges:
                seen_edges.add(key)
                deduped_edges.append(edge)

        chunk_result = {
            "nodes": deduped_nodes,
            "edges": deduped_edges,
            "hyperedges": [],
            "input_tokens": len(all_nodes),
            "output_tokens": len(all_edges),
        }

        output_file = output_dir / f".graphify_chunk_{i:03d}.json"
        output_file.write_text(json.dumps(chunk_result, indent=2))
        print(f"Wrote {output_file}: {len(deduped_nodes)} nodes, {len(deduped_edges)} edges")

    print(f"Processed {len(chunk_files)} chunks from {len(chunk_files) * 20 if chunk_files else 0} files")


if __name__ == "__main__":
    main()
