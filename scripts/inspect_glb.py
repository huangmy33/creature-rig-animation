#!/usr/bin/env python3
"""Inspect GLB structure and geometry before rigging."""
import argparse
import json
import struct
from pathlib import Path


def read_glb_json(path: Path):
    raw = path.read_bytes()
    if len(raw) < 20 or raw[:4] != b"glTF":
        raise ValueError("Not a GLB 2.0 file")
    version, declared = struct.unpack_from("<II", raw, 4)
    if version != 2 or declared != len(raw):
        raise ValueError("Invalid GLB header or declared length")
    json_length, json_type = struct.unpack_from("<II", raw, 12)
    if json_type != 0x4E4F534A:
        raise ValueError("First GLB chunk is not JSON")
    if json_length % 4 or json_length == 0 or 20 + json_length > len(raw):
        raise ValueError("Invalid JSON chunk length")
    offset = 20 + json_length
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise ValueError("Truncated GLB chunk header")
        length, _ = struct.unpack_from("<II", raw, offset)
        if length % 4 or offset + 8 + length > len(raw):
            raise ValueError("Invalid GLB chunk length")
        offset += 8 + length
    data = json.loads(raw[20:20 + json_length].decode("utf-8"))
    if not isinstance(data, dict) or data.get("asset", {}).get("version") != "2.0":
        raise ValueError("Missing glTF 2.0 asset metadata")
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--geometry", action="store_true", help="Also inspect bounds using trimesh")
    args = parser.parse_args()
    path = args.input.resolve()
    data = read_glb_json(path)
    result = {
        "path": str(path), "bytes": path.stat().st_size,
        "generator": data.get("asset", {}).get("generator"),
        "nodes": len(data.get("nodes", [])), "meshes": len(data.get("meshes", [])),
        "skins": len(data.get("skins", [])), "animations": len(data.get("animations", [])),
        "materials": len(data.get("materials", [])), "textures": len(data.get("textures", [])),
        "images": len(data.get("images", [])),
        "externalUris": [item["uri"] for item in [*data.get("buffers", []), *data.get("images", [])]
                         if item.get("uri") and not item["uri"].startswith("data:")],
    }
    if args.geometry:
        import trimesh
        scene = trimesh.load(path, force="scene")
        from mesh_utils import scene_mesh
        mesh = scene_mesh(scene)
        result["geometry"] = {"vertices": len(mesh.vertices), "faces": len(mesh.faces),
            "bounds": mesh.bounds.tolist(), "extents": mesh.extents.tolist(),
            "watertight": bool(mesh.is_watertight)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
