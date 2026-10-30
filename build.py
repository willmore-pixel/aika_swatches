"""Build the swatch site into _site/: every photo in leather/ and canvas/,
cropped to a centre square, resized, and listed in swatches.json (the file name, minus extension, is the swatch's name),
plus the shoe styles in styles/, listed in styles.json. Each swatch has its size in cm (sizes.json, else 30).
下架 (taken off the shelf) items stay in the repo but are listed in hidden.json (swatches, as "kind/name")
or styles/hidden.json (style ids): customers don't see them, and the upload pages read them from
swatches-hidden.json / styles-hidden.json so they can be put back."""
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
SIZE = 1024  # shown on the shoe as a square of up to 30 cm, so keep enough detail

def read_list(path):
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return set()

shutil.rmtree(OUT, ignore_errors=True)
(OUT / "s").mkdir(parents=True)

hidden_sw = read_list(ROOT / "hidden.json")
# sizes.json: how many cm each swatch photo stands for, as {"kind/name": cm} (set by the upload page; left out = 30 cm).
try:
    sizes = json.loads((ROOT / "sizes.json").read_text(encoding="utf-8"))
except Exception:
    sizes = {}
# order.json: the order customers see the swatches in, as ["kind/name", ...] (set with 排序 on the upload page);
# swatches it leaves out (new ones not uploaded through the page) come first, by name. The upload page puts each
# new swatch at the front of order.json itself.
try:
    sw_order = json.loads((ROOT / "order.json").read_text(encoding="utf-8"))
except Exception:
    sw_order = []
sw_rank = {k: i for i, k in enumerate(sw_order)}
swatches, swatches_hidden = [], []
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
        sw = {"name": src.stem, "kind": kind, "file": name, "cm": sizes.get(f"{kind}/{src.stem}", 30)}
        (swatches_hidden if f"{kind}/{src.stem}" in hidden_sw else swatches).append(sw)

by_order = lambda s: (("leather", "canvas").index(s["kind"]), sw_rank.get(f"{s['kind']}/{s['name']}", -1))
swatches.sort(key=by_order)
swatches_hidden.sort(key=by_order)

# Shoe styles (line drawings made into the studio's format by the upload page), one styles/<id>.json each.
# styles/order.json lists ids in the order customers see them; any style it leaves out follows, oldest first.
hidden_st = read_list(ROOT / "styles" / "hidden.json")
styles = []
for src in sorted((ROOT / "styles").glob("*.json")):
    if src.name in ("order.json", "hidden.json"):
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
styles_hidden = [s for s in styles if s["id"] in hidden_st]
styles = [s for s in styles if s["id"] not in hidden_st]
for name, data in (("styles.json", styles), ("styles-hidden.json", styles_hidden)):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

# The shop's upload pages: 色卡 at /upload/, 鞋款 at /style-upload/ (kept apart while the shop tries the second one out).
shutil.copytree(ROOT / "upload", OUT / "upload")
shutil.copytree(ROOT / "style-upload", OUT / "style-upload")

(OUT / "swatches.json").write_text(json.dumps(swatches, ensure_ascii=False, indent=1), encoding="utf-8")
(OUT / "swatches-hidden.json").write_text(json.dumps(swatches_hidden, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(swatches)} swatches ({len(swatches_hidden)} 下架), {len(styles)} styles ({len(styles_hidden)} 下架)")
