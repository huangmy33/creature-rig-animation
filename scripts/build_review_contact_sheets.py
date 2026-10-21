"""Build per-frame and per-view contact sheets from a review manifest."""
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--cell-size", type=int, default=320)
    return parser.parse_args()


def labeled_cell(path, label, cell_size):
    image = Image.open(path).convert("RGB")
    image.thumbnail((cell_size, cell_size), Image.Resampling.LANCZOS)
    cell = Image.new("RGB", (cell_size, cell_size + 30), (24, 27, 35))
    offset = ((cell_size - image.width) // 2, (cell_size - image.height) // 2 + 30)
    cell.paste(image, offset)
    draw = ImageDraw.Draw(cell)
    draw.text((10, 8), label, fill=(240, 243, 248), font=ImageFont.load_default())
    return cell


def contact_sheet(items, output, columns, cell_size):
    cells = [labeled_cell(path, label, cell_size) for label, path in items]
    rows = math.ceil(len(cells) / columns)
    sheet = Image.new("RGB", (columns * cell_size, rows * (cell_size + 30)), (15, 18, 24))
    for index, cell in enumerate(cells):
        sheet.paste(cell, ((index % columns) * cell_size, (index // columns) * (cell_size + 30)))
    sheet.save(output, optimize=True)


def main():
    args = parse_args()
    review_dir = Path(args.review_dir).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else review_dir / "contact-sheets"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = review_dir / "review-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    views = manifest["views"]
    frames = manifest["frames"]
    if not views or not frames or args.cell_size < 64:
        raise ValueError("nonempty views/frames and cell-size >= 64 are required")
    if not all(isinstance(view, str) and view and '/' not in view and '\\' not in view and view not in ('.', '..') for view in views):
        raise ValueError("unsafe view name")
    if not all(isinstance(frame, int) and not isinstance(frame, bool) for frame in frames):
        raise ValueError("frames must be integers")
    expected = [f"{view}-{frame:04d}.png" for view in views for frame in frames]
    expected += manifest.get("detailFiles", [])
    for filename in expected:
        candidate = (review_dir / filename).resolve()
        if not candidate.is_relative_to(review_dir) or not candidate.is_file():
            raise ValueError(f"missing or unsafe review image: {filename}")

    generated = []
    for frame in frames:
        items = []
        for view in views:
            path = review_dir / f"{view}-{frame:04d}.png"
            if path.exists():
                items.append((view, path))
        for filename in manifest.get("detailFiles", []):
            if filename.endswith(f"-{frame:04d}.png"):
                items.append((Path(filename).stem.rsplit("-", 1)[0], review_dir / filename))
        if items:
            output = output_dir / f"frame-{frame:04d}-all-views.png"
            contact_sheet(items, output, min(5, len(items)), args.cell_size)
            generated.append(output.name)

    for view in views:
        items = []
        for frame in frames:
            path = review_dir / f"{view}-{frame:04d}.png"
            if path.exists():
                items.append((f"frame {frame}", path))
        if items:
            output = output_dir / f"timeline-{view}.png"
            contact_sheet(items, output, min(5, len(items)), args.cell_size)
            generated.append(output.name)

    index = {
        "sourceManifest": str(manifest_path),
        "frames": frames,
        "views": views,
        "files": generated,
        "inspectionOrder": [
            "Inspect every frame-*-all-views sheet for occluded and view-dependent defects.",
            "Inspect every timeline-* sheet for temporal popping, drift and loop discontinuity.",
            "Open the original full-resolution render when a sheet reveals a suspicious region.",
        ],
    }
    index_path = output_dir / "contact-sheet-index.json"
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_dir), "index": str(index_path), "sheets": len(generated)}))


if __name__ == "__main__":
    main()
