"""Render front/side/perspective animation keyframes for visual deformation review."""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--frames", nargs="+", type=int)
    args = parser.parse_args(argv)
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.input).resolve()))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.025, 0.03, 0.045)
    camera_data = bpy.data.cameras.new("ReviewCamera")
    camera = bpy.data.objects.new("ReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    coordinates = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    minimum = Vector((min(p.x for p in coordinates), min(p.y for p in coordinates), min(p.z for p in coordinates)))
    maximum = Vector((max(p.x for p in coordinates), max(p.y for p in coordinates), max(p.z for p in coordinates)))
    center = (minimum + maximum) / 2
    extent = max(maximum - minimum)
    camera.data.ortho_scale = extent * 1.45
    light_data = bpy.data.lights.new("ReviewKey", "AREA")
    light_data.energy = 1000
    light_data.size = extent * 4
    light = bpy.data.objects.new("ReviewKey", light_data)
    scene.collection.objects.link(light)
    light.location = center + Vector((extent * 2, -extent * 2, extent * 3))
    views = {"front": Vector((0, -3, 0.15)), "side": Vector((3, 0, 0.15)),
             "perspective": Vector((2.5, -2.5, 1.4))}
    frames = args.frames or [scene.frame_start,
        round(scene.frame_start + (scene.frame_end - scene.frame_start) * 0.25),
        round(scene.frame_start + (scene.frame_end - scene.frame_start) * 0.5),
        round(scene.frame_start + (scene.frame_end - scene.frame_start) * 0.75)]
    for view, direction in views.items():
        camera.location = center + direction.normalized() * extent * 3
        camera.rotation_euler = ((center - camera.location).to_track_quat("-Z", "Y")).to_euler()
        for frame in frames:
            scene.frame_set(frame)
            scene.render.filepath = str(output / f"{view}-{frame:03d}.png")
            bpy.ops.render.render(write_still=True)
    print({"output": str(output), "views": list(views), "frames": frames})


if __name__ == "__main__":
    main()
