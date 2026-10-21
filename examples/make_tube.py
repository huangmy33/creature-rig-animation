"""Generate an original, redistributable low-poly tube fixture. MIT licensed."""
import argparse
from pathlib import Path
import numpy as np
import trimesh


def make_tube():
    rings, sides = 41, 16
    vertices = []
    for i in range(rings):
        t = i / (rings - 1)
        radius = 0.10 - 0.065 * t
        for j in range(sides):
            angle = 2 * np.pi * j / sides
            vertices.append([radius * np.cos(angle), t * 2, radius * np.sin(angle)])
    faces = []
    for i in range(rings - 1):
        for j in range(sides):
            a, b = i * sides + j, i * sides + (j + 1) % sides
            c, d = a + sides, b + sides
            faces.extend([[a, c, b], [b, c, d]])
    vertices.extend([[0, 0, 0], [0, 2, 0]])
    for j in range(sides):
        faces.append([rings * sides, j, (j + 1) % sides])
        faces.append([rings * sides + 1, (rings - 1) * sides + (j + 1) % sides, (rings - 1) * sides + j])
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    mesh.fix_normals()
    mesh.visual.vertex_colors = [48, 166, 181, 255]
    return mesh


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(trimesh.Scene(make_tube()).export(file_type="glb"))
    print(args.output)


if __name__ == "__main__":
    main()
