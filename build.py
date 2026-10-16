"""Build the swatch site into _site/: every photo in leather/ and canvas/,
cropped to a centre square, resized, and listed in swatches.json (the file name, minus extension, is the swatch's name),
plus the shoe styles in styles/, listed in styles.json."""
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

# Shoe styles (line drawings made into the studio's format by the upload page), one styles/<id>.json each.
# styles/order.json lists ids in the order customers see them; any style it leaves out follows, oldest first.
styles = []
for src in sorted((ROOT / "styles").glob("*.json")):
    if src.name == "order.json":
        continue
    try:
        st = json.loads(src.read_text(encoding="utf-8"))
        assert st["items"] and st["parts"] and st["viewBox"]
    except Exception as e:
        print(f"skipped {src.name}: {e}")
        continue
    styles.append({"id": src.stem, **st})
try:
    order = json.loads((ROOT / "styles" / "order.json").read_text(encoding="utf-8"))
except Exception:
    order = []
rank = {k: i for i, k in enumerate(order)}
styles.sort(key=lambda s: (rank.get(s["id"], len(rank)), s.get("added", ""), s["id"]))
(OUT / "styles.json").write_text(json.dumps(styles, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

# The shop's upload page (快速上架: 色卡 and 鞋款), served at /upload/.
shutil.copytree(ROOT / "upload", OUT / "upload")

(OUT / "swatches.json").write_text(json.dumps(swatches, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(swatches)} swatches, {len(styles)} styles")
