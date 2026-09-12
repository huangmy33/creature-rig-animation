"""Re-import an animated GLB in Blender and report real vertex deformation."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy


def evaluated_points(scene, meshes, frame):
    scene.frame_set(frame)
    dependency_graph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in meshes:
        evaluated = obj.evaluated_get(dependency_graph)
        mesh = evaluated.to_mesh()
        points.extend([evaluated.matrix_world @ vertex.co for vertex in mesh.vertices])
        evaluated.to_mesh_clear()
    return points


def comparison(first, second):
    distances = [(a - b).length for a, b in zip(first, second)]
    return {"mean": sum(distances) / len(distances), "max": max(distances),
            "movedOver1mm": sum(value > 0.001 for value in distances)}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--frames", nargs="+", type=int)
    args = parser.parse_args(argv)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.input).resolve()))
    scene = bpy.context.scene
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
    if not meshes or not armatures or not bpy.data.actions:
        raise RuntimeError("expected mesh, armature and animation action")
    frames = args.frames or [scene.frame_start, round((scene.frame_start + scene.frame_end) / 2), scene.frame_end]
    samples = {frame: evaluated_points(scene, meshes, frame) for frame in frames}
    first = samples[frames[0]]
    changes = {f"{frames[0]}_to_{frame}": comparison(first, samples[frame]) for frame in frames[1:]}
    if not any(value["movedOver1mm"] for value in changes.values()):
        raise RuntimeError("animation exists but no vertices moved over 1 mm")
    values = [coordinate for points in samples.values() for point in points for coordinate in point]
    if not all(math.isfinite(value) for value in values):
        raise RuntimeError("non-finite deformed vertex coordinates")
    print(json.dumps({"meshes": len(meshes), "armatures": len(armatures), "vertices": len(first),
        "actions": [action.name for action in bpy.data.actions], "frames": frames, "changes": changes}))


if __name__ == "__main__":
    main()
