"""Generate reusable chain animation profiles in Blender and export an animated GLB."""
import argparse
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_compat import action_fcurves, new_glb_output, validate_motion, check_single_rig


def key_rotation(bone, frame, x=0.0, y=0.0, z=0.0):
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = tuple(math.radians(value) for value in (x, y, z))
    bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone.name)


def animate_undulate(bones, scene, action, amplitude, cycles):
    scene.frame_end = 121
    frames = tuple(range(1, 122, 10))
    if frames[-1] != 121:
        frames += (121,)
    for index, bone in enumerate(bones):
        u = index / max(1, len(bones) - 1)
        for frame in frames:
            time = (frame - 1) / 120
            phase = 2 * math.pi * cycles * time - index * 0.5
            key_rotation(bone, frame,
                x=amplitude * (0.28 + 0.72 * u) * math.sin(phase + math.pi / 2),
                y=amplitude * 0.12 * u * math.sin(phase - 0.6),
                z=amplitude * (0.35 + 0.85 * u) * math.sin(phase))
    loop = True
    return loop


def animate_probe(bones, scene, action, amplitude, cycles):
    scene.frame_end = 97
    for frame in range(1, 98, 4):
        time = (frame - 1) / 96
        wave = 2 * math.pi * cycles * time
        for index, bone in enumerate(bones):
            u = index / max(1, len(bones) - 1)
            strength = amplitude * (0.25 + 0.75 * u)
            key_rotation(bone, frame,
                x=strength * (0.35 * math.sin(wave - index * 0.45) + 0.1 * math.sin(2 * wave)),
                y=strength * 0.22 * math.sin(wave - index * 0.45 + math.pi / 2),
                z=strength * 0.62 * math.sin(wave - index * 0.45))
    loop = True
    return loop


def animate_slap(bones, scene, action, amplitude, cycles):
    scene.frame_end = 72
    for index, bone in enumerate(bones):
        u = index / max(1, len(bones) - 1)
        wind_x = 0.35 * amplitude * (0.35 + 0.65 * u)
        wind_z = 0.20 * amplitude * (0.4 + 0.6 * u)
        hit_x = -0.75 * amplitude * (0.4 + 0.8 * u)
        hit_z = -0.38 * amplitude * (0.45 + 0.75 * u)
        keys = [(1, 0, 0), (10 + index * 0.15, wind_x * 0.45, wind_z * 0.45),
            (20 + index * 0.35, wind_x, wind_z), (29 + index * 0.72, hit_x, hit_z),
            (40 + index * 0.42, hit_x * 0.62, hit_z * 0.70),
            (55 + index * 0.18, -1.2 * (1 - u), 1.8 * (1 - u)), (72, 0, 0)]
        for frame, x, z in keys:
            key_rotation(bone, frame, x=x, y=0.8 * math.sin(u * math.pi) if 20 <= frame <= 45 else 0, z=z)
    return False


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile", choices=["undulate", "probe", "slap"], required=True)
    parser.add_argument("--prefix", default="chain_")
    parser.add_argument("--amplitude", type=float, default=8.0)
    parser.add_argument("--cycles", type=float, default=1.0)
    args = parser.parse_args(argv)
    validate_motion(args.amplitude, args.cycles, args.profile != "slap")
    if args.profile == "slap" and args.cycles != 1:
        parser.error("--cycles is only configurable for undulate and probe")
    output = new_glb_output(args.output)
    armature = next((obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"), None)
    if armature is None:
        raise RuntimeError("no armature found")
    bones = sorted((bone for bone in armature.pose.bones if bone.name.startswith(args.prefix)), key=lambda bone: bone.name)
    if len(bones) < 2:
        raise RuntimeError(f"fewer than two bones match prefix {args.prefix}")
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.render.fps = 24
    armature.animation_data_clear()
    action = bpy.data.actions.new(f"Creature_{args.profile}")
    armature.animation_data_create()
    armature.animation_data.action = action
    loop = {"undulate": animate_undulate, "probe": animate_probe, "slap": animate_slap}[args.profile](
        bones, scene, action, args.amplitude, args.cycles)
    for curve in action_fcurves(action):
        if loop:
            curve.keyframe_points[-1].co[1] = curve.keyframe_points[0].co[1]
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"
    check_single_rig(scene, armature)
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
    print({"output": output.name, "profile": args.profile, "bones": len(bones),
           "frames": [scene.frame_start, scene.frame_end], "fps": scene.render.fps, "loop": loop})


if __name__ == "__main__":
    main()
