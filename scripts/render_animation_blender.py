"""Render keyframe-aware multi-view review images for animated GLB assets."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_compat import action_fcurves, import_gltf


VIEW_PRESETS = {
    "standard": {
        "front": ((0, -1, 0), "ORTHO"),
        "right": ((1, 0, 0), "ORTHO"),
        "perspective_front_right": ((1.4, -1.4, 0.9), "PERSP"),
    },
    "complex": {
        "front": ((0, -1, 0), "ORTHO"),
        "back": ((0, 1, 0), "ORTHO"),
        "left": ((-1, 0, 0), "ORTHO"),
        "right": ((1, 0, 0), "ORTHO"),
        "top": ((0, 0, 1), "ORTHO"),
        "bottom": ((0, 0, -1), "ORTHO"),
        "perspective_front_left": ((-1.4, -1.4, 0.9), "PERSP"),
        "perspective_front_right": ((1.4, -1.4, 0.9), "PERSP"),
        "perspective_back_left": ((-1.4, 1.4, -0.55), "PERSP"),
        "perspective_back_right": ((1.4, 1.4, -0.55), "PERSP"),
    },
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--frames", nargs="+", type=int)
    parser.add_argument("--preset", choices=sorted(VIEW_PRESETS), default="complex")
    parser.add_argument("--views", nargs="+", help="Subset of names in the selected preset")
    parser.add_argument("--detail-objects", nargs="+", help="Mesh object names that need close-up review")
    parser.add_argument("--max-frames", type=int, default=9)
    parser.add_argument("--resolution", type=int, default=640)
    parser.add_argument("--margin", type=float, default=1.28)
    return parser.parse_args(argv)


def evenly_reduce(values, limit):
    values = sorted(set(values))
    if len(values) <= limit:
        return values
    if limit <= 1:
        return [values[0]]
    indices = [round(index * (len(values) - 1) / (limit - 1)) for index in range(limit)]
    return [values[index] for index in sorted(set(indices))]


def animation_range(scene):
    ranges = [action.frame_range for action in bpy.data.actions if any(action_fcurves(action))]
    if not ranges:
        return int(scene.frame_start), int(scene.frame_end)
    return math.floor(min(value[0] for value in ranges)), math.ceil(max(value[1] for value in ranges))


def review_frames(scene, explicit, max_frames):
    start, end = animation_range(scene)
    if explicit:
        invalid = [frame for frame in explicit if frame < start or frame > end]
        if invalid:
            raise RuntimeError(f"review frames outside animation range {start}-{end}: {invalid}")
        return sorted(set(explicit))
    uniform = [round(start + (end - start) * index / 8) for index in range(9)]
    keyed = []
    for action in bpy.data.actions:
        for curve in action_fcurves(action):
            keyed.extend(round(point.co.x) for point in curve.keyframe_points)
    candidates = [frame for frame in keyed + uniform + [start, end] if start <= frame <= end]
    return evenly_reduce(candidates, max(2, max_frames))


def animated_bounds(scene, meshes, frames):
    points = []
    for frame in frames:
        scene.frame_set(frame)
        dependency_graph = bpy.context.evaluated_depsgraph_get()
        for obj in meshes:
            evaluated = obj.evaluated_get(dependency_graph)
            points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
    if not points:
        raise RuntimeError("expected at least one renderable mesh")
    minimum = Vector(tuple(min(point[index] for point in points) for index in range(3)))
    maximum = Vector(tuple(max(point[index] for point in points) for index in range(3)))
    return minimum, maximum


def add_area_light(name, location, energy, size, center):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.size = size
    light = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = ((center - light.location).to_track_quat("-Z", "Y")).to_euler()


def configure_scene(scene, center, extent, resolution):
    engines = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.03, 0.045)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    add_area_light("ReviewKey", center + Vector((extent * 2, -extent * 2, extent * 3)), 1100, extent * 3, center)
    add_area_light("ReviewFill", center + Vector((-extent * 2, -extent, extent)), 650, extent * 2.5, center)
    add_area_light("ReviewRim", center + Vector((0, extent * 2, extent * 2)), 850, extent * 2, center)


def configure_camera(camera, center, dimensions, direction, camera_type, margin):
    direction = Vector(direction).normalized()
    camera.data.type = camera_type
    if camera_type == "ORTHO":
        distance = max(dimensions) * 2.0
        camera.data.ortho_scale = max(max(dimensions), 0.001) * margin
    else:
        camera.data.lens = 52
        radius = max(dimensions.length / 2, 0.001)
        distance = radius / max(math.tan(camera.data.angle / 2), 0.01) * margin
    camera.location = center + direction * distance
    camera.rotation_euler = ((center - camera.location).to_track_quat("-Z", "Y")).to_euler()


def main():
    args = parse_args()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    import_gltf(args.input)
    scene = bpy.context.scene
    meshes = [obj for obj in scene.objects if obj.type == "MESH" and not obj.hide_render]
    frames = review_frames(scene, args.frames, args.max_frames)
    minimum, maximum = animated_bounds(scene, meshes, frames)
    center = (minimum + maximum) / 2
    dimensions = maximum - minimum
    extent = max(max(dimensions), 0.001)
    configure_scene(scene, center, extent, args.resolution)

    camera_data = bpy.data.cameras.new("ReviewCamera")
    camera = bpy.data.objects.new("ReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    preset = VIEW_PRESETS[args.preset]
    if args.views:
        unknown = sorted(set(args.views) - set(preset))
        if unknown:
            raise RuntimeError(f"unknown views for {args.preset}: {unknown}")
        views = {name: preset[name] for name in args.views}
    else:
        views = preset

    files = []
    for view_name, (direction, camera_type) in views.items():
        configure_camera(camera, center, dimensions, direction, camera_type, args.margin)
        for frame in frames:
            scene.frame_set(frame)
            filename = f"{view_name}-{frame:04d}.png"
            scene.render.filepath = str(output / filename)
            bpy.ops.render.render(write_still=True)
            files.append(filename)

    detail_files = []
    if args.detail_objects:
        by_name = {obj.name: obj for obj in meshes}
        unknown = sorted(set(args.detail_objects) - set(by_name))
        if unknown:
            raise RuntimeError(f"unknown detail mesh objects: {unknown}")
        for object_name in args.detail_objects:
            obj = by_name[object_name]
            detail_min, detail_max = animated_bounds(scene, [obj], frames)
            detail_center = (detail_min + detail_max) / 2
            detail_dimensions = detail_max - detail_min
            configure_camera(camera, detail_center, detail_dimensions, (1.4, -1.4, 0.9), "PERSP", args.margin)
            for frame in frames:
                scene.frame_set(frame)
                safe_name = object_name.replace("/", "_").replace("\\", "_")
                filename = f"detail-{safe_name}-{frame:04d}.png"
                scene.render.filepath = str(output / filename)
                bpy.ops.render.render(write_still=True)
                files.append(filename)
                detail_files.append(filename)

    manifest = {
        "input": str(Path(args.input).resolve()),
        "preset": args.preset,
        "views": list(views),
        "frames": frames,
        "detailObjects": args.detail_objects or [],
        "detailFiles": detail_files,
        "animatedBounds": {"min": list(minimum), "max": list(maximum)},
        "files": files,
        "reviewChecklist": [
            "silhouette and motion direction",
            "joint collapse or excessive stretch",
            "self-intersection and limb/body penetration",
            "wing membrane folding and thin-part inversion",
            "head/root stability and unintended whole-body drift",
            "left/right asymmetry where symmetry is expected",
            "first/end pose continuity for looping actions",
        ],
    }
    manifest_path = output / "review-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "manifest": str(manifest_path),
                      "views": list(views), "frames": frames, "images": len(files)}))


if __name__ == "__main__":
    main()
