#!/usr/bin/env python3
"""Render four orthographic point-cloud views with guide bones overlaid."""
import argparse
import json

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from pathlib import Path
from mesh_utils import scene_mesh
from guide_utils import read_guides


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--guides", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    scene = trimesh.load(args.input, force="scene")
    mesh = scene_mesh(scene)
    points, _ = trimesh.sample.sample_surface(mesh, min(70000, max(25000, len(mesh.faces) * 4)))
    center = (mesh.bounds[0] + mesh.bounds[1]) / 2
    points -= center
    extent = np.max(mesh.extents)
    if extent <= 0:
        raise ValueError("mesh has zero extent")
    bones = read_guides(args.guides)["bones"]

    def to_gltf(point):
        x, y, z = point
        return np.array([x, z, -y]) - center

    views = [("Front", np.eye(3)),
        ("Side", np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)),
        ("Top", np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)),
        ("Perspective", trimesh.transformations.euler_matrix(np.radians(18), np.radians(-35), np.radians(12))[:3, :3])]
    size = 800
    canvas = Image.new("RGB", (size * 2, size * 2), (244, 246, 250))
    for view_index, (label, rotation) in enumerate(views):
        transformed = points @ rotation.T
        scale = 0.82 * size / extent
        x = transformed[:, 0] * scale + size / 2
        y = -transformed[:, 1] * scale + size / 2
        depth = transformed[:, 2]
        tile = Image.new("RGB", (size, size), (244, 246, 250))
        draw = ImageDraw.Draw(tile)
        order = np.argsort(depth)
        low, high = float(depth.min()), float(depth.max())
        denominator = max(high - low, 1e-9)
        for index in order[::2]:
            shade = int(55 + 145 * (depth[index] - low) / denominator)
            draw.ellipse((x[index] - 1.2, y[index] - 1.2, x[index] + 1.2, y[index] + 1.2),
                         fill=(35, min(225, shade + 30), min(240, shade + 55)))
        for bone in bones:
            head = to_gltf(bone["head"]) @ rotation.T
            tail = to_gltf(bone["tail"]) @ rotation.T
            coordinates = (head[0] * scale + size / 2, -head[1] * scale + size / 2,
                           tail[0] * scale + size / 2, -tail[1] * scale + size / 2)
            color = (250, 170, 40) if bone.get("role") == "root" else (245, 60, 65)
            draw.line(coordinates, fill=color, width=5)
            draw.ellipse((coordinates[0] - 4, coordinates[1] - 4,
                          coordinates[0] + 4, coordinates[1] + 4), fill=color)
        draw.text((20, 20), label, fill=(15, 23, 42))
        canvas.paste(tile, ((view_index % 2) * size, (view_index // 2) * size))
    Path(args.output).resolve().parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output)
    print(json.dumps({"output": args.output, "bones": len(bones)}))


if __name__ == "__main__":
    main()
