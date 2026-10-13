"""
GrowCircle Brand Asset & Icon Generator.
Generates:
- favicon.ico, favicon.svg
- icon-192.png, icon-512.png (PWA icons)
- icon-maskable-192.png, icon-maskable-512.png (PWA maskable icons with safe padding)
- og-image.png (1200x630 Open Graph preview)
Uses Pillow with 4x supersampling (LANCZOS downsampling) for ultra-sharp vector reproduction.
"""

import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BRAND_ROOT = Path(__file__).resolve().parent
PUBLIC_ICONS = BRAND_ROOT.parent.parent / "web" / "public" / "icons"
PUBLIC_ICONS.mkdir(parents=True, exist_ok=True)

# Brand Color Palette
DEEP_LEAF = (31, 107, 58)  # #1F6B3A
HARVEST_GOLD = (246, 195, 67)  # #F6C343
AMBER = (199, 119, 0)  # #C77700
CREAM = (251, 250, 244)  # #FBFAF4
WHITE = (255, 255, 255)
INK = (27, 27, 24)  # #1B1B18
MUTED = (74, 74, 66)  # #4A4A42


def draw_logo_mark(
    draw: ImageDraw.ImageDraw, offset_x: float, offset_y: float, size: float
) -> None:
    """Draws the canonical GrowCircle logo mark on a square canvas area."""
    # 1. Rounded rectangle background (23% radius)
    corner_radius = size * 0.23
    draw.rounded_rectangle(
        [offset_x, offset_y, offset_x + size, offset_y + size],
        radius=int(corner_radius),
        fill=DEEP_LEAF,
    )

    # 2. White open circle arc (C open to the right)
    center_x = offset_x + size * 0.485
    center_y = offset_y + size * 0.50
    radius = size * 0.255
    stroke_w = int(size * 0.086)

    # Arc from -140 degrees to +140 degrees (leaving opening on right ~ -40 to +40)
    bbox = [
        center_x - radius,
        center_y - radius,
        center_x + radius,
        center_y + radius,
    ]
    draw.arc(bbox, start=40, end=320, fill=WHITE, width=stroke_w)

    # Rounded endcaps on arc
    rad_start = math.radians(40)
    p_start_x = center_x + radius * math.cos(rad_start)
    p_start_y = center_y + radius * math.sin(rad_start)
    cap_r = stroke_w / 2
    draw.ellipse(
        [p_start_x - cap_r, p_start_y - cap_r, p_start_x + cap_r, p_start_y + cap_r], fill=WHITE
    )

    rad_end = math.radians(320)
    p_end_x = center_x + radius * math.cos(rad_end)
    p_end_y = center_y + radius * math.sin(rad_end)
    draw.ellipse([p_end_x - cap_r, p_end_y - cap_r, p_end_x + cap_r, p_end_y + cap_r], fill=WHITE)

    # 3. Harvest Gold leaf across opening, bridging into center
    leaf_pts = [
        (offset_x + size * 0.465, offset_y + size * 0.500),  # stem tip in center
        (offset_x + size * 0.510, offset_y + size * 0.435),
        (offset_x + size * 0.605, offset_y + size * 0.415),
        (offset_x + size * 0.722, offset_y + size * 0.422),  # leaf outer tip
        (offset_x + size * 0.750, offset_y + size * 0.485),
        (offset_x + size * 0.710, offset_y + size * 0.575),
        (offset_x + size * 0.620, offset_y + size * 0.605),
        (offset_x + size * 0.520, offset_y + size * 0.570),
    ]
    draw.polygon(leaf_pts, fill=HARVEST_GOLD)

    # Leaf central vein line
    vein_pts = [
        (offset_x + size * 0.485, offset_y + size * 0.510),
        (offset_x + size * 0.585, offset_y + size * 0.505),
        (offset_x + size * 0.700, offset_y + size * 0.465),
    ]
    draw.line(vein_pts, fill=DEEP_LEAF, width=max(2, int(size * 0.014)), joint="curve")


def generate_icon(target_size: int, is_maskable: bool = False) -> Image.Image:
    """Generates a high-resolution icon downsampled with LANCZOS."""
    scale = 4
    canvas_dim = target_size * scale
    img = Image.new("RGBA", (canvas_dim, canvas_dim), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if is_maskable:
        draw.rectangle([0, 0, canvas_dim, canvas_dim], fill=DEEP_LEAF)
        inner_size = canvas_dim * 0.70
        offset = (canvas_dim - inner_size) / 2
        draw_logo_mark(draw, offset, offset, inner_size)
    else:
        draw_logo_mark(draw, 0, 0, canvas_dim)

    return img.resize((target_size, target_size), Image.Resampling.LANCZOS)


def generate_og_image() -> Image.Image:
    """Generates the 1200x630 Open Graph preview card."""
    scale = 2
    w, h = 1200 * scale, 630 * scale
    img = Image.new("RGBA", (w, h), CREAM)
    draw = ImageDraw.Draw(img)

    bar_height = int(24 * scale)
    draw.rectangle([0, h - bar_height, w, h], fill=DEEP_LEAF)
    draw.rectangle([0, h - bar_height, int(w * 0.28), h], fill=HARVEST_GOLD)

    mark_size = int(320 * scale)
    mark_x = int(120 * scale)
    mark_y = int((h - mark_size - bar_height) / 2)
    draw_logo_mark(draw, mark_x, mark_y, mark_size)

    text_x = int(mark_x + mark_size + 90 * scale)
    base_y = int(mark_y + 40 * scale)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", int(64 * scale))
        font_tagline = ImageFont.truetype("arial.ttf", int(32 * scale))
        font_scripts = ImageFont.truetype("arial.ttf", int(24 * scale))
    except Exception:
        font_title = ImageFont.load_default()
        font_tagline = ImageFont.load_default()
        font_scripts = ImageFont.load_default()

    draw.text((text_x, base_y), "GrowCircle", font=font_title, fill=DEEP_LEAF)
    draw.text(
        (text_x, base_y + int(90 * scale)),
        "Farm to everyone, full circle",
        font=font_tagline,
        fill=AMBER,
    )
    draw.text(
        (text_x, base_y + int(155 * scale)),
        "Telugu: గ్రో సర్కిల్  |  Hindi: ग्रो सर्कल  |  Gujarati: ગ્રો સર્કલ",
        font=font_scripts,
        fill=MUTED,
    )
    badge_y = base_y + int(210 * scale)
    draw.rounded_rectangle(
        [text_x, badge_y, text_x + int(460 * scale), badge_y + int(50 * scale)],
        radius=int(25 * scale),
        fill=DEEP_LEAF,
    )
    draw.text(
        (text_x + int(20 * scale), badge_y + int(14 * scale)),
        "Voice-First Mandi Prices, Buyers & Logistics",
        font=font_scripts,
        fill=WHITE,
    )

    return img.resize((1200, 630), Image.Resampling.LANCZOS)


def main() -> None:
    print("Generating GrowCircle brand icons and assets...")

    svg_source = BRAND_ROOT / "logo-mark.svg"
    favicon_svg = PUBLIC_ICONS / "favicon.svg"
    shutil.copyfile(svg_source, favicon_svg)
    print(f"Copied {favicon_svg}")

    icon_192 = generate_icon(192)
    icon_192.save(PUBLIC_ICONS / "icon-192.png")
    print("Generated icon-192.png")

    icon_512 = generate_icon(512)
    icon_512.save(PUBLIC_ICONS / "icon-512.png")
    print("Generated icon-512.png")

    mask_192 = generate_icon(192, is_maskable=True)
    mask_192.save(PUBLIC_ICONS / "icon-maskable-192.png")
    print("Generated icon-maskable-192.png")

    mask_512 = generate_icon(512, is_maskable=True)
    mask_512.save(PUBLIC_ICONS / "icon-maskable-512.png")
    print("Generated icon-maskable-512.png")

    fav_16 = generate_icon(16)
    fav_32 = generate_icon(32)
    fav_48 = generate_icon(48)
    fav_32.save(
        PUBLIC_ICONS / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[fav_16, fav_48],
    )
    fav_32.save(
        PUBLIC_ICONS.parent / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[fav_16, fav_48],
    )
    print("Generated favicon.ico")

    og_img = generate_og_image()
    og_img.save(PUBLIC_ICONS / "og-image.png")
    print("Generated og-image.png")

    print("Brand assets successfully generated!")


if __name__ == "__main__":
    main()
