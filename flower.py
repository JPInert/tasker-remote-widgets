#!/usr/bin/env python3
"""Render the car-battery widget face: a real-looking flower whose petals light up with the battery.

    ./flower.py <pct> <state> <out.png> [--size 384] [--label CAR]

The flower is ART, not code: art/plate_lit.png, generated with Codex's image tool, with the
constraints this script relies on: 24 petals, one centred at 12 o'clock (measured: gaps at
7.5 + 15k degrees), a big yellow disc (centre 626,613 r~293 of 1254 px), transparent outside.
A different plate must keep those facts, or the PLATE_* constants must be re-measured.

Per reading, code only does what changes with data:
  * petals lit clockwise from 12 o'clock, one per ~4.2 %; unlit = faded grey ghost
  * the label (default "CAR") arched across the top of the yellow disc, the % big in the middle
  * a glyph for the charge cable: bolt = Charging, plug+check = Complete, plug = Stopped,
    struck plug = Disconnected (cable out - NOT car offline)
The phone draws staleness itself (the age sprite, see age_sprites.py), so nothing time-based is
baked in. Fonts: Inter, Inter Display and FontAwesome 4 must be installed.
"""
import math, pathlib, sys
import cairo
import numpy as np
from PIL import Image

PLATE = pathlib.Path(__file__).resolve().parent / "art/plate_lit.png"
PLATE_CX, PLATE_CY, PLATE_DISC_R, PLATE_N = 626, 613, 293, 1254
PETALS = 24
FEATHER = 8.0                     # degrees
INK = (0.23, 0.15, 0.00)          # dark brown on the yellow disc
LOW = (0.78, 0.16, 0.16)
BLUE = (0.05, 0.28, 0.63)
FA = "FontAwesome"
PLUG, BOLT, CHECK = "", "", ""


def face(pct, size):
    """The plate at `size`, with petals past the lit count faded out. Returns RGBA uint8."""
    im = Image.open(PLATE).convert("RGBA").resize((size, size), Image.LANCZOS)
    a = np.array(im).astype(np.float32)
    k = size / PLATE_N
    cx, cy = PLATE_CX * k, PLATE_CY * k
    yy, xx = np.mgrid[0:size, 0:size]
    ang = (np.degrees(np.arctan2(xx - cx, cy - yy)) + 360 + 7.5) % 360   # 0 = 12 o'clock, clockwise, petal-aligned
    lit = round(pct / 100 * PETALS)
    if pct > 0:
        lit = max(1, lit)
    # 0 = unlit, 1 = lit; feathered over FEATHER degrees so the cut through the overlapping petal
    # bases reads as a fade, not a ruler-straight edge (a hard sector cut showed on an earlier render)
    t = (ang + FEATHER) % 360 - FEATHER          # [-F, 360-F): lets the 12 o'clock start edge feather too
    on = np.clip((lit * 360 / PETALS - t) / FEATHER + 0.5, 0, 1) * np.clip(t / FEATHER + 0.5, 0, 1)
    if lit >= PETALS:
        on = np.ones_like(on)
    on = np.where(np.hypot(xx - cx, yy - cy) > PLATE_DISC_R * k * 0.97, on, 1.0)[..., None]
    grey = a[..., :3].mean(axis=2, keepdims=True) * 0.55 + 70
    a[..., :3] = a[..., :3] * on + grey * (1 - on)
    a[..., 3:] = a[..., 3:] * (0.30 + 0.70 * on)
    return a.clip(0, 255).astype(np.uint8), cx, cy, PLATE_DISC_R * k


def to_cairo(rgba):
    """Straight RGBA -> cairo ARGB32 (premultiplied BGRA)."""
    h, w = rgba.shape[:2]
    f = rgba.astype(np.float32)
    al = f[..., 3:4] / 255
    bgra = np.empty_like(rgba)
    bgra[..., 0] = (f[..., 2:3] * al)[..., 0]
    bgra[..., 1] = (f[..., 1:2] * al)[..., 0]
    bgra[..., 2] = (f[..., 0:1] * al)[..., 0]
    bgra[..., 3] = rgba[..., 3]
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    buf = np.zeros((h, stride // 4, 4), np.uint8)
    buf[:, :w] = bgra
    return cairo.ImageSurface.create_for_data(memoryview(buf).cast("B"), cairo.FORMAT_ARGB32, w, h, stride), buf


def centred(cr, text, x, y, family, size, weight=cairo.FONT_WEIGHT_BOLD):
    cr.select_font_face(family, cairo.FONT_SLANT_NORMAL, weight)
    cr.set_font_size(size)
    e = cr.text_extents(text)
    cr.move_to(x - e.x_bearing - e.width / 2, y - e.y_bearing - e.height / 2)
    cr.show_text(text)


def arc_text(cr, text, cx, cy, r, size, spacing=1.22):
    """Letters standing on an arc over the top, centred on 12 o'clock."""
    cr.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(size)
    widths = [cr.text_extents(ch).x_advance * spacing for ch in text]
    a = -math.pi / 2 - sum(widths) / r / 2
    for ch, w in zip(text, widths):
        mid = a + (w / r) / 2
        cr.save()
        cr.translate(cx + r * math.cos(mid), cy + r * math.sin(mid))
        cr.rotate(mid + math.pi / 2)
        e = cr.text_extents(ch)
        cr.move_to(-e.x_bearing - e.width / 2, 0)
        cr.show_text(ch)
        cr.restore()
        a += w / r


def render(pct, state, out, size=384, label="CAR"):
    pct = max(0, min(100, int(pct)))
    rgba, cx, cy, dr = face(pct, size)
    s, _buf = to_cairo(rgba)
    cr = cairo.Context(s)
    u = dr / 100                                  # 1 u = 1 % of the disc radius

    cr.set_source_rgba(*INK, 0.85)
    arc_text(cr, label.upper()[:8], cx, cy, 70 * u, 19 * u)

    num, pc = str(pct), "%"
    cr.select_font_face("Inter Display", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    big = 66 * u if pct < 100 else 54 * u
    cr.set_font_size(big)
    en = cr.text_extents(num)
    cr.set_font_size(big * 0.4)
    ep = cr.text_extents(pc)
    # centre the NUMBER's ink on the disc and let the % hang off to the right (centring the whole
    # "76%" line pushed the big digits visibly left)
    x0 = cx - en.x_bearing - en.width / 2
    base = cy + 22 * u
    cr.set_source_rgb(*(LOW if pct < 20 else INK))
    cr.set_font_size(big)
    cr.move_to(x0, base)
    cr.show_text(num)
    cr.set_font_size(big * 0.4)
    cr.move_to(x0 + en.x_advance + 2 * u, base)
    cr.show_text(pc)

    # the glyph (27u) sits LEFT of centre at -16u: the phone layers the live age sprite just right of it
    # (age_sprites.py draws on the same canvas, widgets/car.js stacks the two images)
    gy, gx = cy + 52 * u, cx - 16 * u
    if state == "Charging":
        cr.set_source_rgb(*BLUE)
        centred(cr, BOLT, gx, gy, FA, 31 * u)
    else:
        cr.set_source_rgba(*INK, 0.85)
        centred(cr, PLUG, gx, gy, FA, 27 * u)
        if state == "Complete":
            centred(cr, CHECK, gx - 15 * u, gy - 13 * u, FA, 12 * u)   # top-left: the plug fills its top-right, the age ring sits right
        elif state == "Disconnected":
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.set_line_width(3.6 * u)
            cr.set_source_rgb(*LOW)
            cr.move_to(gx - 16 * u, gy - 15 * u)
            cr.line_to(gx + 16 * u, gy + 15 * u)
            cr.stroke()
    s.flush()
    s.write_to_png(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    opts = {"--size": "384", "--label": "CAR"}
    for k in opts:
        if k in a:
            i = a.index(k)
            opts[k] = a[i + 1]
            del a[i:i + 2]
    if len(a) != 3:
        sys.exit(__doc__)
    render(int(a[0]), a[1], a[2], int(opts["--size"]), opts["--label"])
