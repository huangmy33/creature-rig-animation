"""Shared validation for guide JSON. Does not require Blender."""
import json
import math
import re
from pathlib import Path


def validate_guides(data):
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("coordinateSystem") != "BLENDER_Z_UP":
        raise ValueError("guides must declare version=1 and coordinateSystem=BLENDER_Z_UP")
    bones = data.get("bones")
    if not isinstance(bones, list) or not 1 <= len(bones) <= 128:
        raise ValueError("guides must contain 1..128 bones")
    names = {}
    for bone in bones:
        if not isinstance(bone, dict):
            raise ValueError("each bone must be an object")
        name = bone.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_]+", name) or name in names:
            raise ValueError("bone names must be unique ASCII alphanumeric/underscore identifiers")
        for key in ("head", "tail"):
            values = bone.get(key)
            if not isinstance(values, list) or len(values) != 3 or not all(
                isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values
            ):
                raise ValueError(f"invalid {key} for {name}")
        if math.dist(bone["head"], bone["tail"]) < 1e-5:
            raise ValueError(f"zero-length bone: {name}")
        meshes = bone.get("meshNames")
        if meshes is not None and (not isinstance(meshes, list) or not all(isinstance(x, str) and x for x in meshes)):
            raise ValueError(f"invalid meshNames for {name}")
        names[name] = bone
    for bone in bones:
        parent = bone.get("parent")
        if parent is not None and (not isinstance(parent, str) or parent not in names):
            raise ValueError(f"missing parent for {bone['name']}")
        visited = {bone["name"]}
        while parent is not None:
            if parent in visited:
                raise ValueError(f"cyclic bone hierarchy at {parent}")
            visited.add(parent)
            ancestor = names.get(parent)
            if ancestor is None:
                raise ValueError(f"missing parent: {parent}")
            parent = ancestor.get("parent")
            if parent is not None and not isinstance(parent, str):
                raise ValueError("parent must be a string or null")
    if not any(b.get("role") != "root" for b in bones):
        raise ValueError("at least one deform bone is required")
    return data


def read_guides(path):
    return validate_guides(json.loads(Path(path).read_text(encoding="utf-8")))
