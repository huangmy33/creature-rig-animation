"""Guide-driven Blender rigging and distance skinning for GLB assets.

Adapted from the user-provided creature-motion-workflow/blender/auto_rig.py on 2026-09-12.
Run with Blender 3.4+ in background mode.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def read_guides(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != 1 or data.get("coordinateSystem") != "BLENDER_Z_UP":
        raise ValueError("guides must declare version=1 and coordinateSystem=BLENDER_Z_UP")
    bones = data.get("bones", [])
    if not 1 <= len(bones) <= 128:
        raise ValueError("guides must contain 1..128 bones")
    names = set()
    for bone in bones:
        name = bone.get("name", "")
        if not name or not name.replace("_", "").isalnum() or name in names:
            raise ValueError("bone names must be unique alphanumeric/underscore identifiers")
        names.add(name)
        for key in ("head", "tail"):
            values = bone.get(key)
            if not isinstance(values, list) or len(values) != 3 or not all(math.isfinite(v) for v in values):
                raise ValueError(f"invalid {key} for {name}")
        if (Vector(bone["head"]) - Vector(bone["tail"])).length < 1e-5:
            raise ValueError(f"zero-length bone: {name}")
    for bone in bones:
        if bone.get("parent") is not None and bone["parent"] not in names:
            raise ValueError(f"missing parent for {bone['name']}")
    return data


def import_model(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(Path(path).resolve()))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    if not meshes:
        raise ValueError("GLB contains no mesh")
    for obj in imported:
        obj.select_set(False)
    return meshes


def create_armature(guides):
    data = bpy.data.armatures.new("CreatureRig")
    armature = bpy.data.objects.new("CreatureRig", data)
    bpy.context.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    armature.show_in_front = True
    bpy.ops.object.mode_set(mode="EDIT")
    editable = {}
    for spec in guides["bones"]:
        bone = data.edit_bones.new(spec["name"])
        bone.head = Vector(spec["head"])
        bone.tail = Vector(spec["tail"])
        editable[spec["name"]] = bone
    for spec in guides["bones"]:
        if spec.get("parent"):
            editable[spec["name"]].parent = editable[spec["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT")
    metadata = []
    for spec in guides["bones"]:
        bone = data.bones[spec["name"]]
        if spec.get("role") == "root":
            bone.use_deform = False
        metadata.append({key: value for key, value in spec.items() if key not in ("head", "tail", "meshNames")})
    armature["rig"] = json.dumps({"version": 1, "kind": guides.get("kind", "custom"), "bones": metadata})
    return armature


def segment_distance(point, head, tail):
    delta = tail - head
    if delta.length_squared < 1e-12:
        return (point - head).length
    amount = max(0.0, min(1.0, (point - head).dot(delta) / delta.length_squared))
    return (point - head - delta * amount).length


def distance_weights(meshes, armature, guides):
    specs = [item for item in guides["bones"] if item.get("role") != "root"]
    for obj in meshes:
        allowed = [item for item in specs if not item.get("meshNames") or obj.name in item["meshNames"]]
        if not allowed:
            raise ValueError(f"no bones available for mesh {obj.name}")
        groups = {spec["name"]: obj.vertex_groups.new(name=spec["name"]) for spec in allowed}
        segments = [(spec["name"], Vector(spec["head"]), Vector(spec["tail"])) for spec in allowed]
        for vertex in obj.data.vertices:
            point = obj.matrix_world @ vertex.co
            candidates = []
            for name, head, tail in segments:
                distance = segment_distance(point, head, tail)
                candidates.append((name, 1.0 / max(distance, 1e-5) ** 2))
            candidates.sort(key=lambda value: value[1], reverse=True)
            chosen = candidates[:4]
            total = sum(weight for _, weight in chosen)
            for name, weight in chosen:
                groups[name].add([vertex.index], weight / total, "REPLACE")
        modifier = obj.modifiers.new(name="CreatureRig", type="ARMATURE")
        modifier.object = armature
        obj.parent = armature
        obj.matrix_parent_inverse = armature.matrix_world.inverted()


def normalize_and_check(meshes, armature):
    deform_names = {bone.name for bone in armature.data.bones if bone.use_deform}
    vertex_count = 0
    for obj in meshes:
        valid_groups = {group.index: group for group in obj.vertex_groups if group.name in deform_names}
        for vertex in obj.data.vertices:
            entries = [(valid_groups[item.group], item.weight) for item in vertex.groups
                       if item.group in valid_groups and item.weight > 1e-8]
            entries.sort(key=lambda value: value[1], reverse=True)
            entries = entries[:4]
            if not entries:
                raise ValueError(f"unweighted vertex {vertex.index} in {obj.name}")
            total = sum(weight for _, weight in entries)
            for group, weight in entries:
                group.add([vertex.index], weight / total, "REPLACE")
            vertex_count += 1
    return vertex_count


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--guides", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--save-blend", action="store_true")
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    if output.suffix.lower() != ".glb":
        raise ValueError("output must end in .glb")
    generated = [output, output.with_suffix(".rigging.json")]
    if args.save_blend:
        generated.append(output.with_suffix(".blend"))
    if any(path.exists() for path in generated):
        raise ValueError("output already exists")
    guides = read_guides(args.guides)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    meshes = import_model(args.input)
    armature = create_armature(guides)
    distance_weights(meshes, armature, guides)
    vertices = normalize_and_check(meshes, armature)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    if args.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(output.with_suffix(".blend")))
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", use_selection=True,
        export_yup=True, export_skins=True, export_animations=False, export_extras=True)
    result = {"status": "success", "meshes": len(meshes), "vertices": vertices,
        "bones": len(guides["bones"]), "maxInfluences": 4, "weightsNormalized": True,
        "coordinateSystem": "Y_UP", "output": output.name}
    output.with_suffix(".rigging.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("rigging failed: " + str(error), file=sys.stderr)
        raise
