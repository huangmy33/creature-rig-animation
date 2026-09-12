#!/usr/bin/env python3
"""Extract a longest centerline from tubular/serpentine GLBs and emit Blender guide JSON."""
import argparse
import json
from pathlib import Path

import networkx as nx
import numpy as np
import trimesh
from skimage.morphology import skeletonize


def axis_value(point, selector):
    axis = "xyz".index(selector[-1])
    value = point[axis]
    return value if selector.startswith("max") else -value


def build_graph(mesh, pitch):
    voxels = mesh.voxelized(pitch).fill()
    skeleton = skeletonize(voxels.matrix)
    indices = np.argwhere(skeleton)
    lookup = {tuple(value): index for index, value in enumerate(indices)}
    graph = nx.Graph()
    graph.add_nodes_from(range(len(indices)))
    for index, point in enumerate(indices):
        for delta_index in np.ndindex(3, 3, 3):
            delta = np.asarray(delta_index) - 1
            if np.all(delta == 0):
                continue
            neighbor = lookup.get(tuple(point + delta))
            if neighbor is not None and neighbor > index:
                graph.add_edge(index, neighbor, weight=float(np.linalg.norm(delta)))
    component = max(nx.connected_components(graph), key=len)
    return voxels, indices, graph.subgraph(component).copy()


def main():
    parser = argparse.ArgumentParser(description="Generate a chain rig guide for a tubular creature")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bones", type=int, default=13, help="Total bones including root")
    parser.add_argument("--pitch", type=float, default=0.008)
    parser.add_argument("--start", choices=["minx", "maxx", "miny", "maxy", "minz", "maxz"])
    parser.add_argument("--end", choices=["minx", "maxx", "miny", "maxy", "minz", "maxz"])
    parser.add_argument("--trim-start", type=float, default=0.04)
    parser.add_argument("--trim-end", type=float, default=0.02)
    parser.add_argument("--kind", choices=["tentacle", "custom"], default="custom")
    parser.add_argument("--prefix", default="chain")
    parser.add_argument("--reverse", action="store_true", help="Reverse the selected centerline before trimming")
    args = parser.parse_args()
    if args.bones < 3:
        raise ValueError("--bones must be at least 3")

    scene = trimesh.load(args.input.resolve(), force="scene")
    mesh = trimesh.util.concatenate([geometry.copy() for geometry in scene.geometry.values()])
    voxels, indices, graph = build_graph(mesh, args.pitch)
    coordinates = voxels.indices_to_points(indices)
    endpoints = [node for node, degree in graph.degree if degree == 1]
    if len(endpoints) < 2:
        endpoints = list(graph.nodes)
    if args.start and args.end:
        start = max(endpoints, key=lambda node: axis_value(coordinates[node], args.start))
        end = max((node for node in endpoints if node != start),
                  key=lambda node: axis_value(coordinates[node], args.end))
    else:
        seed = endpoints[0]
        distance = nx.single_source_dijkstra_path_length(graph, seed, weight="weight")
        start = max(distance, key=distance.get)
        distance, paths = nx.single_source_dijkstra(graph, start, weight="weight")
        end = max(distance, key=distance.get)
    path = nx.shortest_path(graph, start, end, weight="weight")
    points = coordinates[path]
    if args.reverse:
        points = points[::-1]
    kernel = min(13, max(3, (len(points) // 15) | 1))
    padded = np.pad(points, ((kernel // 2, kernel // 2), (0, 0)), mode="edge")
    points = np.vstack([padded[i:i + kernel].mean(axis=0) for i in range(len(points))])
    distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    start_distance = distance[-1] * args.trim_start
    end_distance = distance[-1] * (1 - args.trim_end)
    target = np.linspace(start_distance, end_distance, args.bones)
    sampled = np.column_stack([np.interp(target, distance, points[:, axis]) for axis in range(3)])
    blender = np.column_stack([sampled[:, 0], -sampled[:, 2], sampled[:, 1]])
    root_head = blender[0] - (blender[1] - blender[0]) * 0.55
    bones = [{"name": "root", "parent": None, "head": root_head.tolist(),
              "tail": blender[0].tolist(), "role": "root"}]
    for index in range(len(blender) - 1):
        name = f"{args.prefix}_{index:02d}"
        bones.append({"name": name, "parent": "root" if index == 0 else f"{args.prefix}_{index - 1:02d}",
            "head": blender[index].tolist(), "tail": blender[index + 1].tolist(),
            "role": "chain", "order": index, "side": 0,
            "limits": {"x": [-30, 30], "y": [-30, 30], "z": [-35, 35]}})
    output = {"version": 1, "kind": args.kind, "coordinateSystem": "BLENDER_Z_UP", "bones": bones}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "bones": len(bones), "pathLength": float(distance[-1]),
        "skeletonPoints": len(indices), "endpoints": len(endpoints)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
