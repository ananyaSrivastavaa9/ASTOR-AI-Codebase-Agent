"""
Generate the ASTOR README banner (docs/assets/astor-banner.png).

Run from project root:
    python scripts/generate_banner.py
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "assets" / "astor-banner.png"

WIDTH = 1280
HEIGHT = 400

# ASTOR UI palette (from app.py)
BG_TOP = (20, 14, 33)
BG_BOTTOM = (10, 7, 18)
ACCENT = (143, 110, 242)
ACCENT_SOFT = (201, 167, 255)
INK = (242, 236, 224)
INK_DIM = (154, 146, 171)
INK_FAINT = (114, 107, 133)
LINE = (255, 255, 255, 18)
CREAM = (248, 236, 216)
CREAM_DARK = (241, 221, 191)
CREAM_TEXT = (74, 59, 40)
CHIP_BG = (124, 92, 255, 31)
CHIP_BORDER = (124, 92, 255, 71)
CODE_GREEN = (134, 239, 172)
CODE_BLUE = (147, 197, 253)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if os.name == "nt":
        candidates = [
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/consola.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]

    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue

    return ImageFont.load_default()


def _vertical_gradient(size: tuple[int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, BG_BOTTOM)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def _rounded_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple,
    outline: tuple | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _draw_panel_frame(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    font_title: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_label: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    _rounded_rect(draw, box, 16, fill=(255, 255, 255, 8), outline=(255, 255, 255, 28), width=1)
    x0, y0, _, _ = box
    draw.text((x0 + 16, y0 + 12), title, fill=INK_DIM, font=font_label)
    draw.line([(x0 + 16, y0 + 34), (box[2] - 16, y0 + 34)], fill=(255, 255, 255, 35), width=1)


def _draw_index_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fonts: dict,
) -> None:
    x0, y0, x1, y1 = box
    _draw_panel_frame(draw, box, "INDEX", fonts["label"], fonts["tiny"])

    # Central step number
    draw.text((x0 + 32, y0 + 48), "1", fill=ACCENT, font=fonts["step_num"])
    
    # Larger content area
    tree_x = x0 + 24
    tree_y = y0 + 100
    files = ["app.py", "routes/", "models.py", "utils/"]
    for i, name in enumerate(files):
        indent = 0 if i == 0 else 16
        draw.text((tree_x + indent, tree_y + i * 28), name, fill=INK, font=fonts["mono_med"])

    draw.text((x0 + 16, y1 - 28), "AST Parsing", fill=INK_DIM, font=fonts["tiny"])


def _draw_retrieval_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fonts: dict,
) -> None:
    x0, y0, x1, y1 = box
    _draw_panel_frame(draw, box, "2 · RETRIEVE", fonts["label"], fonts["tiny"])

    lane_y1 = y0 + 70
    lane_y2 = y0 + 118
    end_x = x1 - 40
    start_x = x0 + 30

    draw.text((start_x, lane_y1 - 18), "Vector (ChromaDB)", fill=ACCENT_SOFT, font=fonts["tiny"])
    draw.text((start_x, lane_y2 - 18), "BM25 keywords", fill=ACCENT_SOFT, font=fonts["tiny"])

    for lane_y in (lane_y1, lane_y2):
        draw.line([(start_x, lane_y), (end_x - 50, lane_y)], fill=(143, 110, 242, 120), width=2)

    merge_x = end_x - 30
    merge_y = y0 + 105
    draw.line([(end_x - 50, lane_y1), (merge_x, merge_y)], fill=ACCENT_SOFT, width=2)
    draw.line([(end_x - 50, lane_y2), (merge_x, merge_y)], fill=ACCENT_SOFT, width=2)

    _rounded_rect(draw, (merge_x - 8, merge_y - 22, x1 - 18, merge_y + 48), 8, fill=(36, 28, 58), outline=ACCENT, width=1)
    draw.text((merge_x + 4, merge_y - 12), "def add_url_rule(...)", fill=CODE_GREEN, font=fonts["mono_sm"])
    draw.text((merge_x + 4, merge_y + 10), "scaffold.py · L892", fill=INK_DIM, font=fonts["tiny"])

    draw.text((x0 + 16, y1 - 28), "Hybrid vector + BM25", fill=INK_FAINT, font=fonts["tiny"])


def _draw_answer_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fonts: dict,
) -> None:
    x0, y0, x1, y1 = box
    _draw_panel_frame(draw, box, "3 · ANSWER", fonts["label"], fonts["tiny"])

    card = (x0 + 18, y0 + 48, x1 - 18, y1 - 36)
    _rounded_rect(draw, card, 14, fill=CREAM, outline=(90, 66, 30, 40), width=1)

    cx0, cy0 = card[0] + 16, card[1] + 14
    draw.text((cx0, cy0), "Answer", fill=CREAM_TEXT, font=fonts["card_title"])
    draw.line([(cx0, cy0 + 26), (card[2] - 16, cy0 + 26)], fill=(90, 66, 30, 36), width=1)

    draw.text((cx0, cy0 + 36), "URL rules are added via", fill=CREAM_TEXT, font=fonts["tiny"])
    draw.text((cx0, cy0 + 54), "add_url_rule() in scaffold.py.", fill=CREAM_TEXT, font=fonts["tiny"])

    chip_y = cy0 + 78
    chips = ["flask · scaffold.py", "flask · blueprints.py"]
    chip_x = cx0
    for chip in chips:
        tw = draw.textlength(chip, font=fonts["tiny"])
        w = int(tw) + 18
        _rounded_rect(draw, (chip_x, chip_y, chip_x + w, chip_y + 22), 11, fill=(124, 92, 255, 32), outline=(124, 92, 255, 72), width=1)
        draw.text((chip_x + 9, chip_y + 4), chip, fill=(91, 63, 176), font=fonts["tiny"])
        chip_x += w + 8

    draw.text((x0 + 16, y1 - 28), "Source-grounded citations", fill=INK_FAINT, font=fonts["tiny"])


def generate_banner() -> Path:
    img = _vertical_gradient((WIDTH, HEIGHT)).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Subtle top glow
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((820, -120, 1320, 180), fill=(157, 124, 242, 38))
    glow_draw.ellipse((980, 20, 1280, 220), fill=(255, 140, 120, 18))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    fonts = {
        "brand": _load_font(28, bold=True),
        "tag": _load_font(11),
        "label": _load_font(13, bold=True),
        "tiny": _load_font(11),
        "mono": _load_font(12),
        "mono_sm": _load_font(10),
        "card_title": _load_font(15, bold=True),
    }

    draw.text((36, 28), "ASTOR", fill=ACCENT_SOFT, font=fonts["brand"])
    draw.text((36, 62), "AI codebase agent · index · retrieve · cite", fill=INK_DIM, font=fonts["tag"])

    pad_x = 36
    top = 96
    bottom = HEIGHT - 24
    gap = 18
    panel_w = (WIDTH - pad_x * 2 - gap * 2) // 3

    for i, panel_fn in enumerate((_draw_index_panel, _draw_retrieval_panel, _draw_answer_panel)):
        x0 = pad_x + i * (panel_w + gap)
        box = (x0, top, x0 + panel_w, bottom)
        panel_fn(draw, box, fonts)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(OUTPUT, format="PNG", optimize=True)
    return OUTPUT


if __name__ == "__main__":
    path = generate_banner()
    print(f"Banner written to {path}")
