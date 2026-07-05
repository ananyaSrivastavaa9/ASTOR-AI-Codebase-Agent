"""
Generate ASTOR README banner.

Run:
    python scripts/generate_banner.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "assets" / "astor-banner.png"

WIDTH = 1400
HEIGHT = 420


def load_font(size, bold=False):
    paths = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]

    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)

    return ImageFont.load_default()


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_arrow(draw, x1, y, x2):
    draw.line((x1, y, x2, y), fill=(170, 130, 255), width=4)
    draw.polygon([(x2, y), (x2 - 14, y - 9), (x2 - 14, y + 9)], fill=(170, 130, 255))


def draw_chip(draw, x, y, text, font):
    pad_x = 22
    pad_y = 10
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0] + pad_x * 2
    h = bbox[3] - bbox[1] + pad_y * 2

    rounded(
        draw,
        (x, y, x + w, y + h),
        18,
        fill=(25, 22, 42),
        outline=(115, 82, 210),
        width=1,
    )

    draw.text((x + pad_x, y + pad_y - 2), text, font=font, fill=(225, 218, 245))
    return w


def draw_stage(draw, box, title, subtitle, font_title, font_sub):
    x1, y1, x2, y2 = box

    rounded(
        draw,
        box,
        24,
        fill=(22, 20, 38),
        outline=(132, 94, 255),
        width=2,
    )

    draw.text((x1 + 34, y1 + 32), title, font=font_title, fill=(250, 247, 255))
    draw.text((x1 + 34, y1 + 76), subtitle, font=font_sub, fill=(158, 150, 178))


def generate():
    img = Image.new("RGB", (WIDTH, HEIGHT), (9, 8, 18))
    draw = ImageDraw.Draw(img)

    # soft glows
    draw.ellipse((900, -260, 1580, 500), fill=(32, 18, 68))
    draw.ellipse((-260, 220, 520, 700), fill=(18, 14, 40))

    fonts = {
        "title": load_font(66, True),
        "subtitle": load_font(25),
        "small": load_font(19),
        "stage": load_font(28, True),
        "stage_sub": load_font(18),
        "chip": load_font(17),
    }

    # Header
    draw.text((72, 54), "ASTOR", font=fonts["title"], fill=(200, 160, 255))
    draw.text(
        (78, 132),
        "Retrieval-first AI Codebase Agent",
        font=fonts["subtitle"],
        fill=(230, 225, 245),
    )
    draw.text(
        (80, 172),
        "Index Python repos · retrieve exact source · answer with citations",
        font=fonts["small"],
        fill=(150, 145, 168),
    )

    # Main flow
    y = 250
    stage_w = 285
    stage_h = 125

    repo = (80, y, 80 + stage_w, y + stage_h)
    retrieve = (555, y, 555 + stage_w, y + stage_h)
    answer = (1030, y, 1030 + stage_w, y + stage_h)

    draw_stage(draw, repo, "Index", "Tree-sitter AST chunks", fonts["stage"], fonts["stage_sub"])
    draw_stage(draw, retrieve, "Retrieve", "ChromaDB + BM25", fonts["stage"], fonts["stage_sub"])
    draw_stage(draw, answer, "Cite", "Repo/File grounded answer", fonts["stage"], fonts["stage_sub"])

    draw_arrow(draw, 390, y + 62, 520)
    draw_arrow(draw, 865, y + 62, 995)

    # Chips
    chip_y = 36
    x = 760
    for text in ["85% Retrieval", "20Q Flask Eval", "Gemini Tools"]:
        w = draw_chip(draw, x, chip_y, text, fonts["chip"])
        x += w + 18

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT, format="PNG", optimize=True)
    print(f"Banner written to {OUTPUT}")


if __name__ == "__main__":
    generate()