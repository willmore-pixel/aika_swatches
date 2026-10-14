"""Build the swatch site into _site/: every photo in leather/ and canvas/,
cropped to a centre square, resized, and listed in swatches.json (the file name, minus extension, is the swatch's name)."""
import hashlib, json, shutil
from pathlib import Path
from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener  # iPhone photos
    register_heif_opener()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
SIZE = 1024  # shown as a 30 cm square on the shoe, so keep enough detail

shutil.rmtree(OUT, ignore_errors=True)
(OUT / "s").mkdir(parents=True)

swatches = []
for kind in ("leather", "canvas"):
    for src in sorted((ROOT / kind).iterdir()):
        if src.suffix.lower() not in EXTS:
            continue
        try:
            img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        except Exception as e:
            print(f"skipped {src.name}: {e}")
            continue
        img = ImageOps.fit(img, (SIZE, SIZE), Image.LANCZOS)
        # Named by a hash of the original path so a swatch keeps its address (and customers' saved picks) between builds.
        name = f"s/{kind}-{hashlib.md5(src.name.encode()).hexdigest()[:10]}.jpg"
        img.save(OUT / name, quality=85)
        swatches.append({"name": src.stem, "kind": kind, "file": name})

(OUT / "swatches.json").write_text(json.dumps(swatches, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(swatches)} swatches")
