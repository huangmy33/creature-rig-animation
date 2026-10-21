import copy
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from guide_utils import validate_guides
from inspect_glb import read_glb_json
from blender_compat import action_fcurves, validate_motion, new_glb_output
from mesh_utils import scene_mesh
import numpy as np
import trimesh


def guides():
    return {"version": 1, "coordinateSystem": "BLENDER_Z_UP", "bones": [
        {"name": "root", "head": [0, 0, -1], "tail": [0, 0, 0], "role": "root"},
        {"name": "chain_00", "head": [0, 0, 0], "tail": [0, 0, 1], "parent": "root"}]}


def glb(data):
    payload = json.dumps(data).encode()
    payload += b" " * (-len(payload) % 4)
    return struct.pack("<4sIIII", b"glTF", 2, 20 + len(payload), len(payload), 0x4E4F534A) + payload


class GuideTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_guides(guides())["version"], 1)

    def test_invalid_guides(self):
        mutations = [
            lambda d: d.update(version=2),
            lambda d: d.update(bones=[]),
            lambda d: d["bones"][1].update(name="root"),
            lambda d: d["bones"][1].update(parent="missing"),
            lambda d: d["bones"][1].update(parent="chain_00"),
            lambda d: d["bones"][0].update(parent="chain_00"),
            lambda d: d["bones"][1].update(tail=[0, 0, 0]),
            lambda d: d["bones"][1].update(tail=[0, 0, float("nan")]),
            lambda d: d["bones"][1].update(tail=[0, True, 1]),
            lambda d: d["bones"][1].update(meshNames="mesh"),
            lambda d: d["bones"][1].update(role="root"),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                data = copy.deepcopy(guides())
                mutate(data)
                with self.assertRaises(ValueError):
                    validate_guides(data)


class GlbTests(unittest.TestCase):
    def read(self, raw):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "model.glb"
            path.write_bytes(raw)
            return read_glb_json(path)

    def test_valid(self):
        self.assertEqual(self.read(glb({"asset": {"version": "2.0"}}))["asset"]["version"], "2.0")

    def test_bad_header(self):
        for raw in (b"bad", b"x" * 40, glb({"asset": {"version": "1.0"}})):
            with self.assertRaises(ValueError):
                self.read(raw)

    def test_truncated_json(self):
        raw = bytearray(glb({"asset": {"version": "2.0"}}))
        struct.pack_into("<I", raw, 12, 10000)
        with self.assertRaises(ValueError):
            self.read(raw)

    def test_wrong_declared_length(self):
        with self.assertRaises(ValueError):
            self.read(glb({"asset": {"version": "2.0"}}) + b"junk")


class GeometryTests(unittest.TestCase):
    def test_scene_transform_and_instances(self):
        scene = trimesh.Scene()
        box = trimesh.creation.box()
        scene.add_geometry(box, geom_name="box", node_name="first")
        transform = np.eye(4)
        transform[0, 3] = 10
        scene.graph.update(frame_to="second", matrix=transform, geometry="box")
        mesh = scene_mesh(scene)
        self.assertEqual(len(mesh.vertices), len(box.vertices) * 2)
        self.assertAlmostEqual(mesh.bounds[1, 0], 10.5)

    def test_empty_scene(self):
        with self.assertRaises(ValueError):
            scene_mesh(trimesh.Scene())


class CompatibilityTests(unittest.TestCase):
    def test_legacy_action(self):
        self.assertEqual(list(action_fcurves(SimpleNamespace(fcurves=[1, 2]))), [1, 2])

    def test_layered_action(self):
        bag = SimpleNamespace(fcurves=[3, 4])
        action = SimpleNamespace(is_action_layered=True, layers=[SimpleNamespace(strips=[SimpleNamespace(channelbags=[bag])])])
        self.assertEqual(list(action_fcurves(action)), [3, 4])

    def test_motion_parameters(self):
        validate_motion(8.0, 1.0)
        for amplitude, cycles in ((float("nan"), 1.0), (8.0, 0.5), (-1, 1.0), (8, 0.0)):
            with self.assertRaises(ValueError):
                validate_motion(amplitude, cycles)

    def test_prevent_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "out.glb"
            path.write_bytes(b"original")
            with self.assertRaises(ValueError):
                new_glb_output(path)
            self.assertEqual(path.read_bytes(), b"original")


class CliTests(unittest.TestCase):
    def test_cli_help(self):
        for name in ("inspect_glb.py", "extract_chain_guides.py", "render_guides_overlay.py", "build_review_contact_sheets.py"):
            result = subprocess.run([sys.executable, ROOT / "scripts" / name, "--help"], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_missing_review_image_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "review-manifest.json").write_text(json.dumps({"views": ["front"], "frames": [1]}))
            result = subprocess.run([sys.executable, ROOT / "scripts/build_review_contact_sheets.py", "--review-dir", temp], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"missing or unsafe", result.stderr)

    def test_bad_extraction_parameter_fails(self):
        result = subprocess.run([sys.executable, ROOT / "scripts/extract_chain_guides.py", "--input", "missing.glb", "--output", "never-created.json", "--bones", "129"], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"between 3 and 128", result.stderr)


if __name__ == "__main__":
    unittest.main()
