#!/usr/bin/env python3
"""Render + upload the age-label sprites the car widget layers over the flower.

    ./age_sprites.py                 # render the sprites, upload to <KW_PUB_DIR>/car-<tok>-age/, spot-check one
    ./age_sprites.py --dry [DIR]     # render only (a few samples into DIR if given); no network

Why sprites: the age must be live on the phone, but a Text overlay can't be placed on the flower
reliably. Tasker doesn't tell the layout the widget's size, so dp offsets landed in the petals.
A sprite is the SAME square canvas as the flower with only the label drawn at the glyph's right,
so two `Image` layers with contentScale Fit line up at ANY widget size. widgets/car.js picks
age-<label>.png. Geometry comes from flower.py (glyph at centre-16u, centre+52u).
"""
import math, os, pathlib, subprocess, sys, tarfile, tempfile
import cairo

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flower as cd  # noqa: E402
import make_kw  # noqa: E402

SIZE = 384
INK = (0.23, 0.15, 0.00, 0.80)        # brown on the yellow disc
RED = (0.72, 0.12, 0.12, 0.85)        # a day or more / no reading
# TALLY marks (a clock face and quarter marks were tried first). Each "|" = 10 min; the 5th is a slash through
# the four (50 min); a full hour becomes a DIGIT and the tallies restart: "1 ||" = 1 h 20 min.
# (Roman numerals were tried and dropped: XXIII is too long for the disc.)
#   t{h}_{n}  h = 0..23 hours, n = 0..5 tens of minutes   (t0_0 = under 10 min -> a lone dot)
#   d1..d31   days: red "3d" (d31 = "31d+")               q = no reading: red "?"
# Everything starts just right of the cable glyph and is shrunk to fit inside the yellow disc.
LABELS = ([f"t{h}_{n}" for h in range(24) for n in range(6)] + [f"d{i}" for i in range(1, 32)] + ["q"])
SAMPLES = ("t0_0", "t0_3", "t0_5", "t1_2", "t7_4", "t23_5", "d3", "q")


def roman(n):
    out = ""
    for v, r in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out, n = out + r, n - v
    return out


def render(label, out):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, SIZE, SIZE)
    cr = cairo.Context(s)
    k = SIZE / cd.PLATE_N
    cx, cy, u = cd.PLATE_CX * k, cd.PLATE_CY * k, cd.PLATE_DISC_R * k / 100
    x0, y = cx + 2 * u, cy + 52 * u                     # start just right of the glyph (centre-16u, 27u wide)
    room = math.sqrt(100 ** 2 - 60 ** 2) * u - 2 * u    # to the disc edge, with margin
    cr.select_font_face("Inter Display", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

    if label == "q" or label.startswith("d"):
        cr.set_source_rgba(*RED)
        d = int(label[1:]) if label != "q" else 0
        text = "?" if label == "q" else (f"{d}d" if d < 31 else "31d+")
        cr.set_font_size(30 * u)
        e = cr.text_extents(text)
        dot = 0
        sc = min(1.0, room / (dot * 2 + 3 * u + e.width))
        if dot:
            cr.arc(x0 + dot * sc, y, dot * sc, 0, 2 * math.pi)
            cr.fill()
        cr.set_font_size(30 * u * sc)
        e = cr.text_extents(text)
        cr.move_to(x0 + (2 * dot + 3 * u) * sc - e.x_bearing, y - e.y_bearing - e.height / 2)
        cr.show_text(text)
        s.write_to_png(str(out))
        return

    h, n = (int(v) for v in label[1:].split("_"))
    cr.set_source_rgba(*INK)
    if h == 0 and n == 0:                               # fresh: one small dot
        cr.arc(x0 + 4 * u, y, 3.2 * u, 0, 2 * math.pi)
        cr.fill()
        s.write_to_png(str(out))
        return
    text = str(h) if h else ""                          # plain digits (roman got long: XXIII)
    cr.set_font_size(30 * u)
    tw = cr.text_extents(text).x_advance if text else 0
    # tallies are shorter than the digit so the hour stands out; (with roman numerals "I ||" read as "III")
    pitch, th = 6 * u, 13 * u                            # tally spacing / height
    tally_w = (min(n, 4) - 1) * pitch + 2.6 * u if n else 0
    gap = 8 * u if text and n else 0
    sc = min(1.0, room / max(1e-6, tw + gap + tally_w))
    x = x0
    if text:
        cr.set_font_size(30 * u * sc)
        e = cr.text_extents(text)
        cr.move_to(x - e.x_bearing, y - e.y_bearing - e.height / 2)
        cr.show_text(text)
        x += e.x_advance + gap * sc
    cr.set_source_rgba(*INK[:3], INK[3] * 0.85)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_width(2.2 * u * sc)
    for i in range(min(n, 4)):
        lx = x + 1.3 * u * sc + i * pitch * sc
        cr.move_to(lx, y - th * sc / 2)
        cr.line_to(lx, y + th * sc / 2)
        cr.stroke()
    if n == 5:                                          # the bundle's slash, bottom-left to top-right
        cr.move_to(x - 1.5 * u * sc, y + th * sc * 0.35)
        cr.line_to(x + (3 * pitch + 4.2 * u) * sc, y - th * sc * 0.35)
        cr.stroke()
    s.write_to_png(str(out))


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        for lb in LABELS:
            render(lb, d / f"age-{lb}.png")
        if dry:
            out = pathlib.Path(sys.argv[-1]) if len(sys.argv) > 2 else d
            for lb in SAMPLES:
                render(lb, out / f"age-{lb}.png")
            print(f"rendered {len(LABELS)} labels (dry)")
            sys.exit(0)
        t = make_kw.token()
        tarp = d / "age.tar"
        with tarfile.open(tarp, "w") as tf:
            for lb in LABELS:
                tf.add(d / f"age-{lb}.png", arcname=f"age-{lb}.png")
        host, pubdir = os.environ.get("KW_PUB_HOST"), os.environ.get("KW_PUB_DIR")
        if not host or not pubdir:
            sys.exit("KW_PUB_HOST and KW_PUB_DIR must be set to upload (see kw.env.example)")
        dest = f"{pubdir}/car-{t}-age"
        try:
            subprocess.run(["ssh", "-o", "BatchMode=yes", host,
                            f"mkdir -p {dest}.new && tar -x -C {dest}.new && rm -rf {dest} && mv {dest}.new {dest}"],
                           stdin=open(tarp, "rb"), check=True, capture_output=True, timeout=120)
            code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                   make_kw.PUB + f"car-{t}-age/age-t1_2.png"],
                                  capture_output=True, text=True, timeout=20).stdout
        except subprocess.SubprocessError:
            raise SystemExit("age_sprites: upload failed (details withheld: argv holds the token)") from None
        if code != "200":
            sys.exit(f"age_sprites: spot-check got HTTP {code}")
        print(f"uploaded {len(LABELS)} sprites to car-<tok>-age/, age-t1_2.png -> 200")
