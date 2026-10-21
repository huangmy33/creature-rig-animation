"""Re-import an animated GLB and detect deformation, collapse, explosions and loop discontinuity."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_compat import action_fcurves, import_gltf


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--frames", nargs="+", type=int)
    parser.add_argument("--samples", type=int, default=9)
    parser.add_argument("--max-extent-ratio", type=float, default=4.0)
    parser.add_argument("--min-extent-ratio", type=float, default=0.2)
    parser.add_argument("--max-centroid-drift-ratio", type=float, default=3.0)
    parser.add_argument("--expect-loop", action="store_true")
    parser.add_argument("--loop-tolerance", type=float, default=0.001)
    parser.add_argument("--allow-root-motion", action="store_true")
    return parser.parse_args(argv)


def animation_range(scene):
    ranges = [action.frame_range for action in bpy.data.actions if any(action_fcurves(action))]
    if not ranges:
        return int(scene.frame_start), int(scene.frame_end)
    return math.floor(min(value[0] for value in ranges)), math.ceil(max(value[1] for value in ranges))


def evenly_spaced(start, end, count):
    if count <= 1 or start == end:
        return [start]
    return sorted(set(round(start + (end - start) * index / (count - 1)) for index in range(count)))


def evaluated_points(scene, meshes, frame):
    scene.frame_set(frame)
    dependency_graph = bpy.context.evaluated_depsgraph_get()
    result = {}
    for obj in meshes:
        evaluated = obj.evaluated_get(dependency_graph)
        mesh = evaluated.to_mesh()
        result[obj.name] = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        evaluated.to_mesh_clear()
    return result


def flatten(sample):
    return [point for object_points in sample.values() for point in object_points]


def bounds(points):
    minimum = Vector(tuple(min(point[index] for point in points) for index in range(3)))
    maximum = Vector(tuple(max(point[index] for point in points) for index in range(3)))
    dimensions = maximum - minimum
    return minimum, maximum, dimensions, (minimum + maximum) / 2


def comparison(first, second):
    if set(first) != set(second):
        raise RuntimeError("mesh objects changed between sampled frames")
    distances = []
    per_mesh = {}
    for name in first:
        if len(first[name]) != len(second[name]):
            raise RuntimeError(f"vertex count changed for mesh {name}")
        mesh_distances = [(a - b).length for a, b in zip(first[name], second[name])]
        per_mesh[name] = {
            "mean": sum(mesh_distances) / len(mesh_distances),
            "max": max(mesh_distances),
            "movedOver1mm": sum(value > 0.001 for value in mesh_distances),
        }
        distances.extend(mesh_distances)
    return {
        "mean": sum(distances) / len(distances),
        "max": max(distances),
        "movedOver1mm": sum(value > 0.001 for value in distances),
        "perMesh": per_mesh,
    }


def frame_metrics(sample):
    points = flatten(sample)
    minimum, maximum, dimensions, centroid = bounds(points)
    return {
        "min": list(minimum),
        "max": list(maximum),
        "dimensions": list(dimensions),
        "diagonal": dimensions.length,
        "centroid": list(centroid),
    }


def main():
    args = parse_args()
    thresholds = (args.max_extent_ratio, args.min_extent_ratio, args.max_centroid_drift_ratio, args.loop_tolerance)
    if args.samples < 3 or not all(math.isfinite(x) and x > 0 for x in thresholds) or args.min_extent_ratio >= args.max_extent_ratio:
        raise ValueError("samples >= 3 and finite positive, ordered thresholds are required")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    import_gltf(args.input)
    scene = bpy.context.scene
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
    if not meshes or not armatures or not bpy.data.actions:
        raise RuntimeError("expected mesh, armature and animation action")

    start, end = animation_range(scene)
    if args.frames:
        invalid = [frame for frame in args.frames if frame < start or frame > end]
        if invalid:
            raise RuntimeError(f"validation frames outside animation range {start}-{end}: {invalid}")
        frames = sorted(set(args.frames))
    else:
        frames = evenly_spaced(start, end, args.samples)
    if args.expect_loop:
        frames = sorted(set(frames + [start, end]))
    if len(frames) < 3:
        raise ValueError("select at least three distinct frames to verify deformation")
    samples = {frame: evaluated_points(scene, meshes, frame) for frame in frames}
    all_coordinates = [coordinate for sample in samples.values() for point in flatten(sample) for coordinate in point]
    if not all(math.isfinite(value) for value in all_coordinates):
        raise RuntimeError("non-finite deformed vertex coordinates")

    baseline = samples[frames[0]]
    changes = {str(frame): comparison(baseline, samples[frame]) for frame in frames[1:]}
    if not any(value["movedOver1mm"] for value in changes.values()):
        raise RuntimeError("animation exists but no vertices moved over 1 mm")

    metrics = {str(frame): frame_metrics(samples[frame]) for frame in frames}
    baseline_metrics = metrics[str(frames[0])]
    baseline_diagonal = max(baseline_metrics["diagonal"], 1e-9)
    baseline_centroid = Vector(baseline_metrics["centroid"])
    issues = []
    for frame in frames[1:]:
        current = metrics[str(frame)]
        extent_ratio = current["diagonal"] / baseline_diagonal
        if extent_ratio > args.max_extent_ratio:
            issues.append({"frame": frame, "type": "mesh-explosion", "extentRatio": extent_ratio})
        if extent_ratio < args.min_extent_ratio:
            issues.append({"frame": frame, "type": "mesh-collapse", "extentRatio": extent_ratio})
        drift_ratio = (Vector(current["centroid"]) - baseline_centroid).length / baseline_diagonal
        current["centroidDriftRatio"] = drift_ratio
        if not args.allow_root_motion and drift_ratio > args.max_centroid_drift_ratio:
            issues.append({"frame": frame, "type": "unexpected-root-drift", "driftRatio": drift_ratio})

    loop_comparison = None
    if args.expect_loop:
        loop_comparison = comparison(samples[frames[0]], samples[frames[-1]])
        if loop_comparison["max"] > args.loop_tolerance:
            issues.append({"frame": frames[-1], "type": "loop-discontinuity",
                           "maxVertexDelta": loop_comparison["max"], "tolerance": args.loop_tolerance})

    report = {
        "meshes": len(meshes),
        "armatures": len(armatures),
        "vertices": len(flatten(baseline)),
        "actions": [action.name for action in bpy.data.actions],
        "frames": frames,
        "changesFromFirst": changes,
        "frameMetrics": metrics,
        "loopComparison": loop_comparison,
        "issues": issues,
    }
    print(json.dumps(report))
    if issues:
        raise RuntimeError(f"deformation validation found {len(issues)} issue(s): {issues}")


if __name__ == "__main__":
    main()
