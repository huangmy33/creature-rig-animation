"""Generate a looping flap/flight animation for symmetric wing rigs in Blender."""
import argparse
import math
import sys
from pathlib import Path

import bpy


def set_rotation(bone, frame, x=0, y=0, z=0):
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = tuple(math.radians(value) for value in (x, y, z))
    bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone.name)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--amplitude", type=float, default=28.0)
    parser.add_argument("--cycles", type=float, default=1.0)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    armature = next((obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"), None)
    if armature is None:
        raise RuntimeError("no armature found")
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 97
    armature.animation_data_clear()
    action = bpy.data.actions.new("Creature_Winged_Flight")
    armature.animation_data_create()
    armature.animation_data.action = action
    found = 0
    frames = (1, 13, 25, 37, 49, 61, 73, 85, 97)
    normalized = (0.0, 0.60, 1.0, 0.35, -0.92, -0.55, 0.28, 0.65, 0.0)
    folds = (0, -3, -7, 2, 9, 6, -2, -5, 0)
    for label, side in (("L", -1), ("R", 1)):
        shoulder = armature.pose.bones.get(f"wing_{label}_shoulder")
        elbow = armature.pose.bones.get(f"wing_{label}_elbow")
        wrist = armature.pose.bones.get(f"wing_{label}_wrist")
        if not all((shoulder, elbow, wrist)):
            raise RuntimeError(f"missing {label} shoulder/elbow/wrist wing chain")
        fingers = sorted((bone for bone in armature.pose.bones if bone.name.startswith(f"wing_{label}_finger_")),
                         key=lambda bone: bone.name)
        found += 3 + len(fingers)
        for frame, flap_factor, fold in zip(frames, normalized, folds):
            flap = args.amplitude * flap_factor
            set_rotation(shoulder, frame, x=flap, z=side * fold)
            set_rotation(elbow, frame, x=flap * 0.60, z=side * fold * 1.25)
            set_rotation(wrist, frame, x=flap * 0.34, z=side * fold * 1.55)
            for index, finger in enumerate(fingers):
                set_rotation(finger, frame, x=flap * (0.15 + 0.04 * index),
                             z=side * fold * (1.1 + 0.2 * index))
    root = armature.pose.bones.get("root")
    if root:
        root.rotation_mode = "XYZ"
        for frame, bob, pitch in ((1, 0, 0), (25, -0.012, 2), (49, 0.028, -2.2),
                                  (73, -0.008, 1.2), (97, 0, 0)):
            root.location = (0, 0, bob)
            root.rotation_euler = (math.radians(pitch), 0, 0)
            root.keyframe_insert(data_path="location", frame=frame, group=root.name)
            root.keyframe_insert(data_path="rotation_euler", frame=frame, group=root.name)
    tail_bones = sorted((bone for bone in armature.pose.bones if bone.name.startswith("tail_")), key=lambda bone: bone.name)
    for index, bone in enumerate(tail_bones):
        for frame in frames:
            time = (frame - 1) / 96
            set_rotation(bone, frame, x=2 * math.sin(2 * math.pi * time - index * 0.42),
                         z=4 * math.sin(2 * math.pi * time - index * 0.55))
    for curve in action.fcurves:
        curve.keyframe_points[-1].co[1] = curve.keyframe_points[0].co[1]
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"
    for obj in scene.objects:
        if obj.type == "MESH" and obj.parent is not None:
            world = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = world
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    for obj in scene.objects:
        if obj.type == "MESH":
            obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", use_selection=True,
        export_yup=True, export_skins=True, export_animations=True, export_tangents=True,
        export_extras=True, export_force_sampling=True, export_frame_range=True)
    print({"output": output.name, "bones": found, "frames": [1, 97], "fps": 24, "loop": True})


if __name__ == "__main__":
    main()
