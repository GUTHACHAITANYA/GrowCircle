"""
GrowCircle Play Store & PWA Listing Assets Generator.
Generates:
1. Google Play Store App Icon (512x512 PNG)
2. Google Play Store Feature Graphic (1024x500 PNG)
3. 4 High-Definition Screenshots (1080x1920 PNG portrait mockups):
   - Screenshot 1: Know Today's Mandi Price
   - Screenshot 2: Sell Direct to Buyers & Radar Map
   - Screenshot 3: Book Verified Transport & Guide Rates
   - Screenshot 4: Farm Diary & Season Economics
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).resolve().parent
STORE_DIR = ASSETS_DIR / "store_listing"
STORE_DIR.mkdir(parents=True, exist_ok=True)

# Brand Color Tokens
DEEP_LEAF = (31, 107, 58)  # #1F6B3A
HARVEST_GOLD = (246, 195, 67)  # #F6C343
AMBER = (199, 119, 0)  # #C77700
CREAM = (251, 250, 244)  # #FBFAF4
WHITE = (255, 255, 255)
INK = (27, 27, 24)  # #1B1B18
MUTED = (74, 74, 66)  # #4A4A42
CARD_BG = (255, 255, 255)
BORDER_COLOR = (226, 224, 213)


def draw_logo_mark(draw: ImageDraw.ImageDraw, offset_x: float, offset_y: float, size: float) -> None:
    """Draws the canonical GrowCircle logo mark."""
    corner_radius = size * 0.23
    draw.rounded_rectangle(
        [offset_x, offset_y, offset_x + size, offset_y + size],
        radius=int(corner_radius),
        fill=DEEP_LEAF,
    )
    center_x = offset_x + size * 0.485
    center_y = offset_y + size * 0.50
    radius = size * 0.255
    stroke_w = int(size * 0.086)

    bbox = [center_x - radius, center_y - radius, center_x + radius, center_y + radius]
    draw.arc(bbox, start=40, end=320, fill=WHITE, width=stroke_w)

    rad_start = math.radians(40)
    p_start_x = center_x + radius * math.cos(rad_start)
    p_start_y = center_y + radius * math.sin(rad_start)
    draw.ellipse(
        [p_start_x - stroke_w / 2, p_start_y - stroke_w / 2, p_start_x + stroke_w / 2, p_start_y + stroke_w / 2],
        fill=WHITE,
    )

    rad_end = math.radians(320)
    p_end_x = center_x + radius * math.cos(rad_end)
    p_end_y = center_y + radius * math.sin(rad_end)
    draw.ellipse(
        [p_end_x - stroke_w / 2, p_end_y - stroke_w / 2, p_end_x + stroke_w / 2, p_end_y + stroke_w / 2],
        fill=WHITE,
    )

    leaf_cx = offset_x + size * 0.735
    leaf_cy = offset_y + size * 0.495
    leaf_w = size * 0.16
    leaf_h = size * 0.23
    draw.ellipse(
        [leaf_cx - leaf_w / 2, leaf_cy - leaf_h / 2, leaf_cx + leaf_w / 2, leaf_cy + leaf_h / 2],
        fill=HARVEST_GOLD,
    )


def generate_play_store_icon() -> None:
    """Generates 512x512 Google Play Store app icon."""
    scale = 4
    canvas_size = 512 * scale
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = canvas_size * 0.06
    mark_size = canvas_size - (margin * 2)
    draw_logo_mark(draw, margin, margin, mark_size)

    final_img = img.resize((512, 512), Image.Resampling.LANCZOS)
    out_path = STORE_DIR / "play_store_icon_512x512.png"
    final_img.save(out_path, format="PNG")
    print(f"[OK] Generated Play Store Icon: {out_path}")


def generate_feature_graphic() -> None:
    """Generates 1024x500 Google Play Store Feature Graphic."""
    scale = 2
    w = 1024 * scale
    h = 500 * scale
    img = Image.new("RGBA", (w, h), DEEP_LEAF)
    draw = ImageDraw.Draw(img)

    # Decorative background circles
    draw.ellipse([-100, -100, 400, 400], fill=(24, 88, 47, 255))
    draw.ellipse([w - 300, h - 300, w + 200, h + 200], fill=(38, 128, 70, 255))

    # Logo Mark on the left
    mark_size = 240 * scale
    mark_x = 100 * scale
    mark_y = 130 * scale
    draw_logo_mark(draw, mark_x, mark_y, mark_size)

    # Text Area on the right
    text_x = int(400 * scale)
    title_y = int(160 * scale)
    sub_y = int(260 * scale)
    tag_y = int(320 * scale)

    # Title: GrowCircle
    draw.text((text_x, title_y), "GrowCircle", fill=WHITE, font_size=int(72 * scale))

    # Multilingual script line
    draw.text((text_x, sub_y), "గ్రో సర్కిల్  •  ग्रो सर्कल  •  ગ્રો સર્કલ", fill=HARVEST_GOLD, font_size=int(26 * scale))

    # Tagline
    draw.text((text_x, tag_y), '"Farm to everyone, full circle"', fill=(230, 245, 235), font_size=int(24 * scale))

    final_img = img.resize((1024, 500), Image.Resampling.LANCZOS)
    out_path = STORE_DIR / "feature_graphic_1024x500.png"
    final_img.save(out_path, format="PNG")
    print(f"[OK] Generated Feature Graphic: {out_path}")


def generate_screenshot(filename: str, headline: str, subline: str, card_title: str, card_content: list[str]) -> None:
    """Generates high-definition 1080x1920 portrait store mockup."""
    w, h = 1080, 1920
    img = Image.new("RGBA", (w, h), CREAM)
    draw = ImageDraw.Draw(img)

    # Top brand bar
    draw.rectangle([0, 0, w, 280], fill=DEEP_LEAF)
    draw_logo_mark(draw, 60, 60, 140)
    draw.text((230, 85), "GrowCircle", fill=WHITE, font_size=58)
    draw.text((230, 160), "గ్రో సర్కిల్ • Andhra Pradesh", fill=HARVEST_GOLD, font_size=32)

    # Headline Hero Box
    draw.rectangle([60, 340, w - 60, 560], fill=WHITE, outline=BORDER_COLOR, width=3)
    draw.text((100, 380), headline, fill=DEEP_LEAF, font_size=46)
    draw.text((100, 460), subline, fill=MUTED, font_size=32)

    # Main UI Card Mockup
    card_top = 620
    card_bot = 1680
    draw.rounded_rectangle([60, card_top, w - 60, card_bot], radius=40, fill=WHITE, outline=BORDER_COLOR, width=4)

    # Card Title
    draw.text((110, card_top + 60), card_title, fill=INK, font_size=44)
    draw.line([110, card_top + 130, w - 110, card_top + 130], fill=BORDER_COLOR, width=2)

    # Card Content Items
    item_y = card_top + 180
    for _idx, item in enumerate(card_content):
        # Bullet pill
        pill_top = item_y + 10
        draw.rounded_rectangle([110, pill_top, w - 110, pill_top + 160], radius=24, fill=(247, 246, 240), outline=BORDER_COLOR, width=2)
        draw.text((150, pill_top + 30), item, fill=INK, font_size=36)
        item_y += 200

    # Bottom Footer Tag
    draw.text((w // 2 - 260, 1780), "DPDP Act 2023 Compliant • Official Agmarknet Data", fill=MUTED, font_size=24)

    out_path = STORE_DIR / filename
    img.save(out_path, format="PNG")
    print(f"[OK] Generated Screenshot: {out_path}")


def main() -> None:
    print("Generating GrowCircle Store Listing & PWA Assets...")
    generate_play_store_icon()
    generate_feature_graphic()

    # 4 High-definition store screenshots
    generate_screenshot(
        filename="screenshot_1_prices.png",
        headline="KNOW TODAY'S MANDI PRICE",
        subline="Official daily rates for 3 nearest mandis in Telugu, Hindi & English",
        card_title="Live Mandi Arrivals • Guntur District",
        card_content=[
            "Guntur Mandi: ₹25.0 / kg (Amruthapani Banana) • Nearest",
            "Tenali Mandi: ₹18.0 / kg (Robusta Banana) • 28 km away",
            "Vijayawada Mandi: ₹27.0 / kg • NTR District",
            "Seasonality: Normal & Fair Price this month (0% markup)",
        ],
    )

    generate_screenshot(
        filename="screenshot_2_direct_selling.png",
        headline="SELL DIRECT TO VERIFIED BUYERS",
        subline="Colleges, hostel mess contractors, hotels and shopkeepers",
        card_title="50 km Institutional Match Radar",
        card_content=[
            "ANU Campus Hostel: Needs 500 kg weekly • Verified Buyer",
            "3-Photo Checklist: Whole lot, close-up, opened crate",
            "Masked Call Bridge: Connect without sharing personal phone",
            "Delivery Handshake: 6-digit Delivery OTP released at gate",
        ],
    )

    generate_screenshot(
        filename="screenshot_3_transport.png",
        headline="BOOK VERIFIED LOCAL TRANSPORT",
        subline="Goods autos, mini-trucks and freight pooling with guide rates",
        card_title="Top 3 Matched Drivers Near Farm Gate",
        card_content=[
            "Driver Ramesh: Mini-Truck (1.2 t) • Valid RC & FC • 4.9★",
            "Indicative Guide Rate: ₹350 base + ₹25 / km (Distance transparent)",
            "Freight Pooling: Group nearby farm loads to same destination",
            "Safe Handshake: 4-digit Pickup OTP releases load to driver",
        ],
    )

    generate_screenshot(
        filename="screenshot_4_farm_diary.png",
        headline="FARM DIARY & SEASON ECONOMICS",
        subline="Voice entry with read-back confirmation • P&L per acre",
        card_title="Kharif Plot Ledger & Mandi Benchmark",
        card_content=[
            "Voice-First Entry: Spoken note transcribed & confirmed",
            "Profit / Loss per Acre: ₹37,600 / acre net profit",
            "Break-Even Price: ₹8.16 / kg cost of production",
            "Direct Selling Dividend: +₹4.30/kg (+17.8%) vs Mandi avg",
        ],
    )

    print("\n[SUCCESS] All Play Store and PWA listing assets generated successfully!")


if __name__ == "__main__":
    main()
