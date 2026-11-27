#!/usr/bin/env python3
"""Check generated BPMN diagrams for XML, graph, geometry and routing issues."""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from pathlib import Path

GRID = 10


def check_file(path: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    counts = Counter()
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        return [f"XML parse: {exc}"], counts
    root = tree.getroot()
    cells = root.findall(".//mxCell")
    ids = [c.get("id") for c in cells]
    duplicates = [i for i, n in Counter(ids).items() if n != 1]
    for ident in duplicates:
        errors.append(f"ID trùng: {ident}")
    by_id = {c.get("id"): c for c in cells}
    vertices = {i: c for i, c in by_id.items() if c.get("vertex") == "1"}
    edges = {i: c for i, c in by_id.items() if c.get("edge") == "1"}
    counts["node"] = sum(c.get("bpmnKind") not in {"pool", "lane", "legend"} for c in vertices.values())
    counts["edge"] = len(edges)
    counts["straight"] = 0
    counts["waypoint"] = 0
    categories = Counter()

    # Geometry is stored relative to the parent container. Accumulate origins.
    abs_boxes: dict[str, tuple[float, float, float, float]] = {}
    active: set[str] = set()

    def abs_box(ident: str) -> tuple[float, float, float, float] | None:
        if ident in abs_boxes:
            return abs_boxes[ident]
        if ident in active:
            errors.append(f"Parent loop at {ident}")
            return None
        cell = by_id.get(ident)
        if cell is None:
            return None
        active.add(ident)
        g = cell.find("mxGeometry")
        if g is None or g.get("width") is None or g.get("height") is None:
            active.remove(ident)
            return None
        x, y, w, h = (float(g.get(k, "0")) for k in ("x", "y", "width", "height"))
        parent = cell.get("parent")
        pg = abs_box(parent) if parent and parent not in {"0", "1"} else (0.0, 0.0, 0.0, 0.0)
        if pg:
            x += pg[0]
            y += pg[1]
        active.remove(ident)
        abs_boxes[ident] = (x, y, w, h)
        return abs_boxes[ident]

    def owning_pool(ident: str) -> str | None:
        current = by_id.get(ident)
        seen = set()
        while current is not None:
            if current.get("bpmnKind") == "pool":
                return current.get("id")
            parent = current.get("parent")
            if not parent or parent in seen:
                return None
            seen.add(parent)
            current = by_id.get(parent)
        return None

    for ident, cell in vertices.items():
        parent = cell.get("parent")
        if parent not in by_id:
            errors.append(f"Parent không tồn tại: node {ident} -> {parent}")
            categories["parent"] += 1
        g = cell.find("mxGeometry")
        if g is None:
            errors.append(f"Thiếu geometry: {ident}")
            categories["geometry"] += 1
            continue
        for key in ("x", "y", "width", "height"):
            val = g.get(key)
            if val is not None and abs(float(val) / GRID - round(float(val) / GRID)) > 1e-8:
                errors.append(f"Không chia hết {GRID}px: {ident}.{key}={val}")
                categories["grid"] += 1
        box = abs_box(ident)
        if box is None:
            continue
        if cell.get("bpmnKind") not in {"pool", "lane", "legend"}:
            parent_box = abs_box(parent)
            if parent_box and (box[0] < parent_box[0] or box[1] < parent_box[1] or box[0] + box[2] > parent_box[0] + parent_box[2] or box[1] + box[3] > parent_box[1] + parent_box[3]):
                errors.append(f"Node nằm ngoài lane: {ident}")
                categories["lane_bounds"] += 1

    # No overlapping flow nodes.
    flow_nodes = [(i, abs_boxes[i]) for i, c in vertices.items() if c.get("bpmnKind") not in {"pool", "lane", "legend"} and i in abs_boxes]
    for idx, (a_id, a) in enumerate(flow_nodes):
        for b_id, b in flow_nodes[idx + 1 :]:
            if max(a[0], b[0]) < min(a[0] + a[2], b[0] + b[2]) and max(a[1], b[1]) < min(a[1] + a[3], b[1] + b[3]):
                errors.append(f"Node chồng lấn: {a_id} và {b_id}")
                categories["overlap"] += 1

    # Edge endpoint, BPMN pool, anchor and orthogonal route checks.
    adj: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    indegree = Counter()
    outdegree = Counter()
    association_degree = Counter()
    for ident, edge in edges.items():
        src, dst = edge.get("source"), edge.get("target")
        if not src or not dst or src not in vertices or dst not in vertices:
            errors.append(f"Edge thiếu source/target hợp lệ: {ident} ({src} -> {dst})")
            categories["edge_endpoints"] += 1
            continue
        kind = edge.get("edgeKind", "sequence")
        if kind == "association":
            association_degree[src] += 1
            association_degree[dst] += 1
            if owning_pool(src) != owning_pool(dst):
                errors.append(f"Association khác pool: {ident}")
                categories["association_scope"] += 1
        elif kind == "message":
            if owning_pool(src) == owning_pool(dst):
                errors.append(f"Message Flow cùng pool: {ident}")
                categories["message_scope"] += 1
        elif kind in {"sequence", "default", "conditional"}:
            if owning_pool(src) != owning_pool(dst):
                errors.append(f"Sequence Flow khác pool: {ident}")
                categories["sequence_scope"] += 1
        if kind in {"sequence", "default", "conditional", "message"}:
            adj[src].add(dst)
            reverse[dst].add(src)
            outdegree[src] += 1
            indegree[dst] += 1
        style = edge.get("style", "")
        ports = {}
        for item in style.split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                if key in {"exitX", "exitY", "entryX", "entryY"}:
                    ports[key] = value
        if not all(k in ports for k in ("exitX", "exitY", "entryX", "entryY")) or "exitPerimeter=0" not in style or "entryPerimeter=0" not in style:
            errors.append(f"Thiếu điểm ra/vào cố định: {ident}")
            categories["anchors"] += 1
            continue
        sb, tb = abs_box(src), abs_box(dst)
        if not sb or not tb:
            continue
        start = (sb[0] + sb[2] * float(ports["exitX"]), sb[1] + sb[3] * float(ports["exitY"]))
        end = (tb[0] + tb[2] * float(ports["entryX"]), tb[1] + tb[3] * float(ports["entryY"]))
        g = edge.find("mxGeometry")
        arr = g.find("Array") if g is not None else None
        points = []
        if arr is not None:
            for p in arr.findall("mxPoint"):
                points.append((float(p.get("x", "0")), float(p.get("y", "0"))))
                for key in ("x", "y"):
                    val = float(p.get(key, "0"))
                    if abs(val / GRID - round(val / GRID)) > 1e-8:
                        errors.append(f"Waypoint lệch lưới: {ident} {key}={val}")
                        categories["grid"] += 1
        points = [start, *points, end]
        if arr is None:
            counts["straight"] += 1
            if abs(start[0] - end[0]) > 1e-8 and abs(start[1] - end[1]) > 1e-8:
                dx, dy = abs(start[0] - end[0]), abs(start[1] - end[1])
                errors.append(f"LỆCH: edge {ident}, độ lệch x={dx:g}px y={dy:g}px")
                categories["alignment"] += 1
        else:
            counts["waypoint"] += 1
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            if abs(x1 - x2) > 1e-8 and abs(y1 - y2) > 1e-8:
                errors.append(f"Đoạn chéo: {ident} ({x1:g},{y1:g}) -> ({x2:g},{y2:g})")
                categories["diagonal"] += 1
                continue
            for node_id, box in flow_nodes:
                if node_id in {src, dst}:
                    continue
                x, y, w, h = box
                crosses = (abs(y1 - y2) < 1e-8 and y < y1 < y + h and max(min(x1, x2), x) < min(max(x1, x2), x + w)) or (abs(x1 - x2) < 1e-8 and x < x1 < x + w and max(min(y1, y2), y) < min(max(y1, y2), y + h))
                if crosses:
                    errors.append(f"Edge xuyên node: {ident} qua {node_id}")
                    categories["edge_crossing"] += 1

    # Process-level start, end, gateways, and reachability.
    starts = [i for i, c in vertices.items() if c.get("bpmnKind") == "start"]
    ends = [i for i, c in vertices.items() if c.get("bpmnKind") in {"end", "error_end"}]
    if not starts:
        errors.append("Process không có Start Event")
        categories["start_end"] += 1
    if not ends:
        errors.append("Process không có End Event")
        categories["start_end"] += 1
    for ident, cell in vertices.items():
        kind = cell.get("bpmnKind")
        if kind in {"pool", "lane", "legend"}:
            continue
        if kind == "data_store":
            if association_degree[ident] == 0:
                errors.append(f"Data Store không có Data Association: {ident}")
                categories["orphan"] += 1
        elif kind == "start" and outdegree[ident] == 0 or kind in {"end", "error_end"} and indegree[ident] == 0 or kind not in {"start", "end", "error_end", "data_store"} and (indegree[ident] == 0 or outdegree[ident] == 0):
            errors.append(f"Node mồ côi/cụt: {ident} ({kind})")
            categories["orphan"] += 1
        if kind == "gateway":
            outgoing = [c for c in edges.values() if c.get("source") == ident and c.get("edgeKind") in {"sequence", "default", "conditional", "message"}]
            if len(outgoing) < 2:
                errors.append(f"Gateway không có ít nhất hai nhánh: {ident}")
                categories["gateway"] += 1
            for edge in outgoing:
                if not (edge.get("value") or "").strip():
                    errors.append(f"Nhánh gateway thiếu nhãn: {edge.get('id')}")
                    categories["gateway_labels"] += 1
    can_reach_end = set(ends)
    queue = deque(ends)
    while queue:
        current = queue.popleft()
        for prev in reverse[current]:
            if prev not in can_reach_end:
                can_reach_end.add(prev)
                queue.append(prev)
    for ident, cell in vertices.items():
        if cell.get("bpmnKind") not in {"pool", "lane", "legend", "data_store"} and ident not in can_reach_end:
            errors.append(f"Không có đường tới End: {ident}")
            categories["unreachable_end"] += 1

    counts["errors"] = len(errors)
    counts["categories"] = dict(categories)
    return errors, counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help=".drawio files (defaults to generated drawio directory)")
    args = parser.parse_args()
    base = Path(__file__).resolve().parent / "drawio"
    paths = [Path(p) for p in args.files] if args.files else sorted(base.glob("*.drawio"))
    if not paths:
        raise SystemExit("Không tìm thấy file .drawio")
    total_nodes = total_edges = total_straight = total_waypoints = total_errors = 0
    failed = False
    for path in paths:
        errors, counts = check_file(path)
        total_nodes += counts.get("node", 0)
        total_edges += counts.get("edge", 0)
        total_straight += counts.get("straight", 0)
        total_waypoints += counts.get("waypoint", 0)
        total_errors += counts.get("errors", 0)
        print(f"{path.name}: {counts.get('node', 0)} node, {counts.get('edge', 0)} cạnh; thẳng={counts.get('straight', 0)}, waypoint={counts.get('waypoint', 0)}, lỗi={counts.get('errors', 0)}")
        if errors:
            failed = True
            for error in errors:
                print(f"  LỖI: {error}")
            print(f"  Theo loại: {counts.get('categories', {})}")
    print(f"TỔNG: {len(paths)} file, {total_nodes} node, {total_edges} cạnh, {total_straight} cạnh không waypoint đã kiểm tra thẳng hàng, {total_waypoints} cạnh có waypoint, {total_errors} lỗi")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
