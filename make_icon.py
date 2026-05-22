#!/usr/bin/env python3
"""Generate BenchFlow app icon — test tube, green liquid, clean biotech style."""

import math, os, random, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

OUT_DIR = Path(__file__).parent
ICONSET = OUT_DIR / "AppIcon.iconset"
ICONSET.mkdir(exist_ok=True)


def vgradient(size, c1, c2):
    """True vertical gradient: row y has color lerp(c1,c2, y/size)."""
    arr = np.zeros((size, size, 4), dtype=np.uint8)
    c1, c2 = np.array(c1, float), np.array(c2, float)
    for y in range(size):
        t = y / max(size - 1, 1)
        arr[y, :] = np.clip(c1 * (1 - t) + c2 * t, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def vgradient_strip(size, y0, y1, c1, c2):
    """RGBA image with gradient only between rows y0 and y1."""
    arr = np.zeros((size, size, 4), dtype=np.uint8)
    c1, c2 = np.array(c1, float), np.array(c2, float)
    h = y1 - y0
    if h <= 0:
        return Image.fromarray(arr, "RGBA")
    for y in range(y0, y1):
        t = (y - y0) / max(h - 1, 1)
        arr[y, :] = np.clip(c1 * (1 - t) + c2 * t, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def tube_mask_img(size, x0, y0, x1, y1, r):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([x0, y0, x1, y1], radius=r, fill=255)
    return m


def make_icon(size: int) -> Image.Image:
    S = size
    rng = random.Random(42)

    # ── 1. Background gradient (vertical, light blue → faint green-white) ──────
    bg = vgradient(S,
                   (219, 234, 254, 255),   # blue-200  #DBEAFE
                   (240, 253, 244, 255))    # green-50  #F0FDF4
    bg.putalpha(rounded_mask(S, int(S * 0.22)))

    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    canvas = Image.alpha_composite(canvas, bg)

    # ── 2. Soft white inner glow card ──────────────────────────────────────────
    card = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    m = int(S * 0.055)
    ImageDraw.Draw(card).rounded_rectangle(
        [m, m, S - m, S - m], radius=int(S * 0.17), fill=(255, 255, 255, 150)
    )
    card = card.filter(ImageFilter.GaussianBlur(S * 0.012))
    canvas = Image.alpha_composite(canvas, card)

    # ── Test tube geometry ─────────────────────────────────────────────────────
    cx = S // 2
    tw     = int(S * 0.195)            # outer width
    wall   = max(int(S * 0.013), 2)
    t_top  = int(S * 0.135)
    t_bot  = int(S * 0.845)
    t_h    = t_bot - t_top
    t_left  = cx - tw // 2
    t_right = cx + tw // 2
    t_r    = tw // 2                   # fully rounded ends

    i_left  = t_left + wall
    i_right = t_right - wall
    i_bot   = t_bot - wall
    i_w     = i_right - i_left
    i_r     = i_w // 2

    liq_ratio = 0.60
    liq_y0    = t_top + int(t_h * (1 - liq_ratio))   # liquid surface

    # ── 3. Drop shadow ─────────────────────────────────────────────────────────
    shd = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    so = int(S * 0.022)
    ImageDraw.Draw(shd).rounded_rectangle(
        [t_left + so, t_top + so, t_right + so, t_bot + so],
        radius=t_r, fill=(80, 140, 200, 55)
    )
    shd = shd.filter(ImageFilter.GaussianBlur(S * 0.024))
    canvas = Image.alpha_composite(canvas, shd)

    # ── 4. Glass tube body ─────────────────────────────────────────────────────
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        [t_left, t_top, t_right, t_bot],
        radius=t_r,
        fill=(228, 242, 255, 215),
        outline=(147, 197, 253, 255),
        width=wall
    )

    # ── 5. Green liquid (gradient strip clipped to inner tube) ─────────────────
    liq = vgradient_strip(S, liq_y0, i_bot + 1,
                          (74, 222, 128, 255),    # green-400
                          (21, 128,  61, 255))    # green-700

    inner_m = tube_mask_img(S, i_left, t_top, i_right, i_bot, i_r)
    rect_m  = Image.new("L", (S, S), 0)
    ImageDraw.Draw(rect_m).rectangle([0, liq_y0, S, S], fill=255)
    combined = ImageChops.multiply(inner_m, rect_m)

    liq_a = liq.getchannel("A")
    liq.putalpha(ImageChops.multiply(liq_a, combined))
    canvas = Image.alpha_composite(canvas, liq)

    # ── 6. Green glow around liquid ────────────────────────────────────────────
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gp = int(S * 0.018)
    ImageDraw.Draw(glow).rounded_rectangle(
        [t_left - gp, liq_y0 - gp, t_right + gp, t_bot + gp],
        radius=t_r + gp, fill=(74, 222, 128, 38)
    )
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.024))
    canvas = Image.alpha_composite(canvas, glow)

    # ── 7. Re-draw tube outline on top ─────────────────────────────────────────
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        [t_left, t_top, t_right, t_bot],
        radius=t_r, fill=None,
        outline=(147, 197, 253, 255), width=wall
    )

    # ── 8. Meniscus line at liquid surface ─────────────────────────────────────
    men_h = max(int(S * 0.009), 2)
    draw.ellipse(
        [i_left + wall, liq_y0 - men_h // 2,
         i_right - wall, liq_y0 + men_h // 2],
        fill=(34, 197, 94, 255)
    )

    # ── 9. Glass highlight strip (left side reflection) ────────────────────────
    hl_arr = np.zeros((S, S, 4), dtype=np.uint8)
    hx0 = t_left + wall * 2
    hx1 = t_left + wall * 2 + max(int(tw * 0.11), 4)
    hy0 = t_top + int(t_h * 0.06)
    hy1 = t_top + int(t_h * 0.46)
    for y in range(hy0, hy1):
        tf = (y - hy0) / max(hy1 - hy0, 1)
        a  = int(195 * (1 - tf ** 0.55))
        hl_arr[y, hx0:hx1] = [255, 255, 255, a]

    hl = Image.fromarray(hl_arr, "RGBA")
    tube_m = tube_mask_img(S, t_left, t_top, t_right, t_bot, t_r)
    hl_a = hl.getchannel("A")
    hl.putalpha(ImageChops.multiply(hl_a, tube_m))
    canvas = Image.alpha_composite(canvas, hl)

    # ── 10. Bubbles in liquid ──────────────────────────────────────────────────
    draw = ImageDraw.Draw(canvas)
    if size >= 64:
        n = 5 if size >= 256 else 3
        for _ in range(n):
            bx = rng.randint(i_left + max(int(i_w * 0.18), 4),
                             i_right - max(int(i_w * 0.25), 4))
            by = rng.randint(liq_y0 + int(t_h * 0.06),
                             i_bot - max(int(t_h * 0.12), 4))
            br = max(rng.randint(int(S * 0.007), int(S * 0.018)), 2)
            draw.ellipse([bx - br, by - br, bx + br, by + br],
                         fill=(255, 255, 255, 108),
                         outline=(167, 243, 208, 160),
                         width=max(int(br * 0.25), 1))

    # ── 11. Tube lip / mouth at top ────────────────────────────────────────────
    lip_x = int(tw * 0.12)
    lip_h = max(int(S * 0.028), 4)
    draw.rounded_rectangle(
        [t_left - lip_x, t_top - lip_h,
         t_right + lip_x, t_top + lip_h // 2],
        radius=max(int(lip_h * 0.45), 2),
        fill=(210, 230, 252, 225),
        outline=(147, 197, 253, 255),
        width=max(wall - 1, 1)
    )

    return canvas


# ── Export all sizes ───────────────────────────────────────────────────────────
print("Rendering 1024×1024 master…")
master = make_icon(1024)

# Preview with white background for verification
preview = Image.new("RGB", (1024, 1024), (255, 255, 255))
preview.paste(master, mask=master.getchannel("A"))
preview.save(str(OUT_DIR / "AppIcon_preview.png"))
print("  → AppIcon_preview.png (white bg, for review)")

ICONSET_MAP = {
    "icon_16x16.png":      16,
    "icon_16x16@2x.png":   32,
    "icon_32x32.png":      32,
    "icon_32x32@2x.png":   64,
    "icon_128x128.png":    128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png":    256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png":    512,
    "icon_512x512@2x.png": 1024,
}

for fname, sz in ICONSET_MAP.items():
    img = master if sz == 1024 else master.resize((sz, sz), Image.LANCZOS)
    img.save(str(ICONSET / fname))
    print(f"  → {fname} ({sz}×{sz})")

print("\nRunning iconutil…")
r = subprocess.run(
    ["iconutil", "-c", "icns", str(ICONSET), "-o", str(OUT_DIR / "AppIcon.icns")],
    capture_output=True, text=True
)
if r.returncode == 0:
    print("  ✓ AppIcon.icns created")
else:
    print(f"  ✗ iconutil error: {r.stderr}")
print("Done.")
