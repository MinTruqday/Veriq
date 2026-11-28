#!/usr/bin/env python3
"""Generate editable diagrams.net BPMN files from coordinate-free JSON specs."""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path


# Central style table. The BPMN shape names and properties below were checked
# against jgraph/drawio's shapes/bpmn/mxBpmnShape2.js (upstream `dev`).
STYLE = {
    "pool": "swimlane;horizontal=0;startSize=30;rounded=0;html=1;collapsible=0;fillColor=#F4F6F8;swimlaneFillColor=#FFFFFF;strokeColor=#667085;fontColor=#1F2937;fontSize=13;",
    "lane": "swimlane;horizontal=0;startSize=30;rounded=0;html=1;collapsible=0;fillColor={fill};swimlaneFillColor=#FFFFFF;strokeColor={stroke};fontColor=#172B4D;fontSize=12;",
    "start": "shape=mxgraph.bpmn.shape;perimeter=ellipsePerimeter;outline=standard;symbol=general;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#27864B;strokeWidth=2;fontColor=#172B4D;fontSize=11;",
    "end": "shape=mxgraph.bpmn.shape;perimeter=ellipsePerimeter;outline=end;symbol=general;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#B42318;strokeWidth=3;fontColor=#172B4D;fontSize=11;",
    "error_end": "shape=mxgraph.bpmn.shape;perimeter=ellipsePerimeter;outline=end;symbol=error;whiteSpace=wrap;html=1;fillColor=#FFF1F0;strokeColor=#B42318;strokeWidth=3;fontColor=#7A271A;fontSize=11;",
    "user_task": "shape=mxgraph.bpmn.task2;whiteSpace=wrap;rectStyle=rounded;size=10;html=1;container=1;expand=0;collapsible=0;taskMarker=user;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;fontColor=#172B4D;fontSize=11;",
    "service_task": "shape=mxgraph.bpmn.task2;whiteSpace=wrap;rectStyle=rounded;size=10;html=1;container=1;expand=0;collapsible=0;taskMarker=service;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;fontColor=#172B4D;fontSize=11;",
    "gateway": "shape=mxgraph.bpmn.gateway2;html=1;perimeter=rhombusPerimeter;outline=none;symbol=none;gwType=exclusive;fillColor=#FFF2CC;strokeColor=#B8860B;strokeWidth=1.5;fontColor=#172B4D;fontSize=10;",
    "data_store": "shape=datastore;html=1;labelPosition=center;verticalLabelPosition=bottom;align=center;verticalAlign=top;fillColor=#F2F4F7;strokeColor=#667085;strokeWidth=1.5;fontColor=#344054;fontSize=10;",
    "sequence": "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;strokeColor=#344054;strokeWidth=1.5;labelBackgroundColor=#FFFFFF;fontColor=#172B4D;fontSize=10;",
    "default": "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;startArrow=dash;strokeColor=#344054;strokeWidth=1.5;labelBackgroundColor=#FFFFFF;fontColor=#172B4D;fontSize=10;",
    "association": "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;dashed=1;dashPattern=1 4;endArrow=open;endFill=0;strokeColor=#667085;strokeWidth=1.2;labelBackgroundColor=#FFFFFF;fontColor=#344054;fontSize=9;",
    "legend": "text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;strokeColor=none;fillColor=none;fontColor=#344054;fontSize=11;",
}

GRID = 10
COL_STEP = 180
FIRST_CX = 230
LANE_X = 30
LANE_HEIGHT = 400  # three logical rows with 40 px vertical padding
ROW_STEP = 120
ROW0_CY = 80
NODE_SIZE = {"start": (40, 40), "end": (40, 40), "error_end": (40, 40), "gateway": (60, 60), "user_task": (120, 80), "service_task": (120, 80), "data_store": (60, 60)}


def xml_text(parent: ET.Element, tag: str, value: str, attrs: dict[str, str] | None = None) -> ET.Element:
    return ET.SubElement(parent, tag, attrs or {})


def geom(parent: ET.Element, x: int, y: int, w: int, h: int) -> None:
    ET.SubElement(parent, "mxGeometry", {"x": str(x), "y": str(y), "width": str(w), "height": str(h), "as": "geometry"})


def style_for_node(node: dict, lane: dict) -> str:
    kind = node["type"]
    if kind in ("start", "end", "error_end", "gateway", "data_store"):
        return STYLE[kind]
    task_style = "user_task" if node.get("task_type", "user") == "user" else "service_task"
    return STYLE[task_style].format(fill=node.get("fill", lane["fill"]), stroke=node.get("stroke", lane["stroke"]))


def cell_id(prefix: str, value: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in value)
    return f"{prefix}_{safe}"


def node_center(node: dict, lane_y: int) -> tuple[int, int]:
    return FIRST_CX + node["col"] * COL_STEP, lane_y + ROW0_CY + node.get("row", 0) * ROW_STEP


def edge_ports_and_waypoints(src: dict, dst: dict, positions: dict, lanes: dict, edge: dict) -> tuple[dict[str, str], list[tuple[int, int]]]:
    sx, sy = positions[src["id"]]
    tx, ty = positions[dst["id"]]
    sw, sh = NODE_SIZE[src["type"]]
    tw, th = NODE_SIZE[dst["type"]]
    route = edge.get("route")
    if route == "loop_below":
        lane = lanes[src["lane"]]
        rail_y = lane["y"] + LANE_HEIGHT - 20
        return ({"exitX": "0.5", "exitY": "1", "entryX": "0.5", "entryY": "1"}, [(sx, rail_y), (tx, rail_y)])
    if route == "lane_gap":
        source_lane, target_lane = lanes[src["lane"]], lanes[dst["lane"]]
        if target_lane["y"] > source_lane["y"]:
            rail_y = source_lane["y"] + LANE_HEIGHT - 20
            return ({"exitX": "0.5", "exitY": "1", "entryX": "0.5", "entryY": "0"}, [(sx, rail_y), (tx, rail_y)])
        rail_y = source_lane["y"] + 20
        return ({"exitX": "0.5", "exitY": "0", "entryX": "0.5", "entryY": "1"}, [(sx, rail_y), (tx, rail_y)])
    if sy == ty:
        if tx >= sx:
            return ({"exitX": "1", "exitY": "0.5", "entryX": "0", "entryY": "0.5"}, [])
        return ({"exitX": "0", "exitY": "0.5", "entryX": "1", "entryY": "0.5"}, [])
    if sx == tx:
        if ty > sy:
            return ({"exitX": "0.5", "exitY": "1", "entryX": "0.5", "entryY": "0"}, [])
        return ({"exitX": "0.5", "exitY": "0", "entryX": "0.5", "entryY": "1"}, [])
    # Route vertical sections through the free gap between the two endpoint columns.
    mid_x = int(round(((sx + sw // 2 + tx - tw // 2) / 2) / GRID) * GRID)
    if src["type"] == "gateway" and ty > sy:
        ports = {"exitX": "0.5", "exitY": "1", "entryX": "0", "entryY": "0.5"}
        return ports, [(sx, ty)]
    elif src["type"] == "gateway" and ty < sy:
        ports = {"exitX": "0.5", "exitY": "0", "entryX": "0", "entryY": "0.5"}
        return ports, [(sx, ty)]
    elif dst["type"] == "gateway" and ty > sy:
        ports = {"exitX": "1", "exitY": "0.5", "entryX": "0.5", "entryY": "0"}
        return ports, [(tx, sy)]
    elif dst["type"] == "gateway" and ty < sy:
        ports = {"exitX": "1", "exitY": "0.5", "entryX": "0.5", "entryY": "1"}
        return ports, [(tx, sy)]
    elif tx > sx:
        ports = {"exitX": "1", "exitY": "0.5", "entryX": "0", "entryY": "0.5"}
    else:
        ports = {"exitX": "0", "exitY": "0.5", "entryX": "1", "entryY": "0.5"}
    return ports, [(mid_x, sy), (mid_x, ty)]


def build(spec: dict, out_path: Path) -> dict[str, int]:
    lanes_in = spec["lanes"]
    max_col = max(n["col"] for n in spec["nodes"])
    pool_width = int(math.ceil((FIRST_CX + COL_STEP * max_col + 220) / GRID) * GRID)
    pool_height = LANE_HEIGHT * len(lanes_in)
    page_width = pool_width + 360
    page_height = max(pool_height + 100, 760)

    root = ET.Element("mxfile", {"host": "app.diagrams.net", "modified": "2026-11-28T00:00:00.000Z", "agent": "Codex", "version": "26.0.0", "type": "device"})
    diagram = ET.SubElement(root, "diagram", {"id": spec["id"], "name": spec["name"]})
    model = ET.SubElement(diagram, "mxGraphModel", {"dx": str(page_width), "dy": str(page_height), "grid": "1", "gridSize": "10", "guides": "1", "tooltips": "1", "connect": "1", "arrows": "1", "fold": "1", "page": "1", "pageScale": "1", "pageWidth": str(page_width), "pageHeight": str(page_height), "math": "0", "shadow": "0"})
    mxroot = ET.SubElement(model, "root")
    ET.SubElement(mxroot, "mxCell", {"id": "0"})
    ET.SubElement(mxroot, "mxCell", {"id": "1", "parent": "0"})

    pool_id = "pool_veriq"
    pool = ET.SubElement(mxroot, "mxCell", {"id": pool_id, "value": "Quy trình", "style": STYLE["pool"], "vertex": "1", "parent": "1", "bpmnKind": "pool"})
    geom(pool, 0, 0, pool_width, pool_height)
    lane_map: dict[str, dict] = {}
    lane_ids: dict[str, str] = {}
    for ix, lane in enumerate(lanes_in):
        lid = cell_id("lane", lane["id"])
        lane_ids[lane["id"]] = lid
        y = ix * LANE_HEIGHT
        lane_map[lane["id"]] = {**lane, "y": y, "height": LANE_HEIGHT}
        cell = ET.SubElement(mxroot, "mxCell", {"id": lid, "value": lane["name"], "style": STYLE["lane"].format(fill=lane["fill"], stroke=lane["stroke"]), "vertex": "1", "parent": pool_id, "bpmnKind": "lane"})
        geom(cell, LANE_X, ix * LANE_HEIGHT, pool_width - LANE_X, LANE_HEIGHT)

    node_ids = {n["id"]: cell_id("node", n["id"]) for n in spec["nodes"]}
    positions: dict[str, tuple[int, int]] = {}
    by_node = {n["id"]: n for n in spec["nodes"]}
    for node in spec["nodes"]:
        lane = lane_map[node["lane"]]
        cx, cy = node_center(node, lane["y"])
        w, h = NODE_SIZE[node["type"]]
        # All x/y coordinates are calculated from centers, never stored in the spec.
        local_x = cx - LANE_X - w // 2
        local_y = (cy - lane["y"]) - h // 2
        cell = ET.SubElement(mxroot, "mxCell", {"id": node_ids[node["id"]], "value": node["label"], "style": style_for_node(node, lane), "vertex": "1", "parent": lane_ids[node["lane"]], "bpmnKind": node["type"], "specId": node["id"]})
        geom(cell, local_x, local_y, w, h)
        positions[node["id"]] = (cx, cy)

    edge_counts = {"straight": 0, "waypoint": 0}
    for edge in spec["edges"]:
        src, dst = by_node[edge["from"]], by_node[edge["to"]]
        ports, points = edge_ports_and_waypoints(src, dst, positions, lane_map, edge)
        style = STYLE[edge.get("type", "sequence")]
        style += ";".join(f"{key}={value}" for key, value in ports.items()) + ";exitPerimeter=0;entryPerimeter=0;"
        cell = ET.SubElement(mxroot, "mxCell", {"id": cell_id("edge", edge["id"]), "value": edge.get("label", ""), "style": style, "edge": "1", "parent": "1", "source": node_ids[edge["from"]], "target": node_ids[edge["to"]], "edgeKind": edge.get("type", "sequence"), "specId": edge["id"]})
        g = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        if points:
            arr = ET.SubElement(g, "Array", {"as": "points"})
            for x, y in points:
                ET.SubElement(arr, "mxPoint", {"x": str(x), "y": str(y)})
            edge_counts["waypoint"] += 1
        else:
            edge_counts["straight"] += 1

    legend = ET.SubElement(mxroot, "mxCell", {"id": "legend", "value": "<b>Chú giải</b><br>Viền xanh: bắt đầu<br>Viền đỏ: kết thúc<br>Nền vàng: câu hỏi/rẽ nhánh<br>Nền xanh: thao tác người dùng<br>Nền tím: xử lý tự động<br>Mũi tên liền: luồng tuần tự<br>Nhánh có nhãn: điều kiện từ mã nguồn", "style": STYLE["legend"], "vertex": "1", "parent": "1", "bpmnKind": "legend"})
    geom(legend, pool_width + 40, 30, 280, 190)

    ET.indent(root, space="  ")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(out_path, encoding="UTF-8", xml_declaration=True)
    return {"nodes": len(spec["nodes"]), "edges": len(spec["edges"]), **edge_counts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", nargs="*", help="JSON specs (defaults to all specs next to this script)")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    paths = [Path(p) for p in args.spec] if args.spec else sorted((here / "specs").glob("*.json"))
    if not paths:
        raise SystemExit("Không tìm thấy spec JSON")
    for path in paths:
        spec = json.loads(path.read_text(encoding="utf-8"))
        target = here / "drawio" / spec["file_name"]
        counts = build(spec, target)
        print(f"Đã tạo {target}: {counts['nodes']} node, {counts['edges']} cạnh ({counts['straight']} thẳng, {counts['waypoint']} có waypoint)")


if __name__ == "__main__":
    main()
