#!/usr/bin/env python3
"""Reproducible smoke test; run from any directory. No proprietary assets/API keys."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--blender", default="blender", help="Executable name or absolute path")
    p.add_argument("--output-dir", type=Path, default=ROOT / "temp_data/demo")
    p.add_argument("--render", action="store_true", help="Also render review images")
    args = p.parse_args()
    out = args.output_dir.resolve()
    if out.exists():
        p.error("output-dir already exists; choose a new directory")
    blender = shutil.which(args.blender)
    node = shutil.which("node")
    if not blender or not node:
        p.error("Blender and Node.js must be installed and on PATH (or use --blender)")
    out.mkdir(parents=True)
    results = []

    def run(label, command):
        print(f"[{label}]", flush=True)
        result = subprocess.run([str(x) for x in command], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / f"{label}.log").write_text(result.stdout, encoding="utf-8")
        results.append({"stage": label, "returncode": result.returncode})
        (out / "smoke-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        if result.returncode:
            print(result.stdout, file=sys.stderr)
            raise SystemExit(result.returncode)

    py = sys.executable
    run("fixture", [py, ROOT / "examples/make_tube.py", "--output", out / "input.glb"])
    run("inspect", [py, ROOT / "scripts/inspect_glb.py", out / "input.glb", "--geometry"])
    run("extract", [py, ROOT / "scripts/extract_chain_guides.py", "--input", out / "input.glb", "--output", out / "guides.json", "--bones", "9", "--pitch", "0.02", "--start", "miny", "--end", "maxy"])
    run("overlay", [py, ROOT / "scripts/render_guides_overlay.py", "--input", out / "input.glb", "--guides", out / "guides.json", "--output", out / "guides-overlay.png"])
    base = [blender, "--background", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1", "-t", "1"]
    run("rig", base + ["-P", ROOT / "scripts/auto_rig_blender.py", "--", "--input", out / "input.glb", "--guides", out / "guides.json", "--output", out / "rigged.glb", "--save-blend"])
    for profile in ("undulate", "probe", "slap"):
        target = out / f"{profile}.glb"
        run(f"animate-{profile}", base + [out / "rigged.blend", "-P", ROOT / "scripts/animate_chain_blender.py", "--", "--output", target, "--profile", profile, "--amplitude", "8"])
        flags = ["--expect-loop"] if profile != "slap" else []
        run(f"deformation-{profile}", base + ["-P", ROOT / "scripts/validate_animation_blender.py", "--", "--input", target, "--samples", "9"] + flags)
        run(f"gltf-{profile}", [node, ROOT / "scripts/validate_glb.mjs", target])
    if args.render:
        run("render", base + ["-P", ROOT / "scripts/render_animation_blender.py", "--", "--input", out / "undulate.glb", "--output-dir", out / "review", "--preset", "standard", "--max-frames", "5", "--resolution", "320"])
        run("contact-sheets", [py, ROOT / "scripts/build_review_contact_sheets.py", "--review-dir", out / "review"])
    print(f"PASS: {len(results)} stages. Logs and assets: {out}")
    print("Smoke tests do not replace artistic review on real creature models.")


if __name__ == "__main__":
    main()
