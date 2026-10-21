"""Small compatibility helpers for legacy and layered Blender actions."""
from pathlib import Path
import math


def action_fcurves(action):
    if getattr(action, "is_action_layered", False):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", ()):
                    yield from bag.fcurves
    else:
        yield from getattr(action, "fcurves", ())


def check_single_rig(scene, armature):
    rigs = [o for o in scene.objects if o.type == "ARMATURE"]
    if len(rigs) != 1 or rigs[0] != armature:
        raise ValueError("animation export requires exactly one armature")
    for obj in scene.objects:
        if obj.type == "MESH":
            modifiers = [m for m in obj.modifiers if m.type == "ARMATURE"]
            if len(modifiers) != 1 or modifiers[0].object != armature:
                raise ValueError(f"mesh must reference the selected rig: {obj.name}")


def import_gltf(path):
    import bpy
    options = {"filepath": str(Path(path).resolve())}
    if "disable_bone_shape" in bpy.ops.import_scene.gltf.get_rna_type().properties:
        options["disable_bone_shape"] = True
    bpy.ops.import_scene.gltf(**options)


def new_glb_output(value):
    path = Path(value).resolve()
    if path.suffix.lower() != ".glb":
        raise ValueError("output must end in .glb")
    if path.exists():
        raise ValueError("output already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def validate_motion(amplitude, cycles, loop=True):
    if not math.isfinite(amplitude) or amplitude <= 0:
        raise ValueError("amplitude must be finite and positive")
    if not math.isfinite(cycles) or cycles <= 0 or (loop and not cycles.is_integer()):
        raise ValueError("loop cycles must be a positive integer")
