from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "assets" / "astor-banner.png"

WIDTH, HEIGHT = 1400, 420

def font(size, bold=False):
    paths = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def rounded(draw, box, r, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def arrow(draw, x1, y, x2):
    draw.line((x1, y, x2, y), fill=(184, 137, 255), width=4)
    draw.polygon([(x2, y), (x2 - 16, y - 10), (x2 - 16, y + 10)], fill=(184, 137, 255))

def chip(draw, x, y, text, f):
    b = draw.textbbox((0, 0), text, font=f)
    w = b[2] - b[0] + 34
    h = b[3] - b[1] + 18
    rounded(draw, (x, y, x + w, y + h), 18, (25, 22, 42), (126, 91, 230), 1)
    draw.text((x + 17, y + 8), text, font=f, fill=(224, 218, 245))
    return w

def stage(draw, box, num, title, sub, fnum, ftitle, fsub):
    x1, y1, x2, y2 = box
    rounded(draw, box, 24, (22, 20, 38), (135, 92, 255), 2)
    rounded(draw, (x1 + 30, y1 + 28, x1 + 88, y1 + 58), 15, (124, 92, 255))
    draw.text((x1 + 47, y1 + 32), num, font=fnum, fill=(255, 255, 255))
    draw.text((x1 + 30, y1 + 78), title, font=ftitle, fill=(250, 247, 255))
    draw.text((x1 + 30, y1 + 116), sub, font=fsub, fill=(163, 154, 184))

def generate():
    img = Image.new("RGB", (WIDTH, HEIGHT), (8, 7, 16))
    draw = ImageDraw.Draw(img)

    draw.ellipse((850, -300, 1600, 520), fill=(35, 20, 76))
    draw.ellipse((-330, 230, 560, 760), fill=(20, 16, 48))

    f = {
        "headline": font(38, True),
        "sub": font(21),
        "chip": font(16),
        "num": font(15, True),
        "stage": font(31, True),
        "stage_sub": font(18),
    }

    draw.text((70, 68), "Code Intelligence Pipeline", font=f["headline"], fill=(245, 241, 255))
    draw.text((72, 120), "Parse code structure · retrieve exact source · cite every answer", font=f["sub"], fill=(166, 158, 185))

    x = 800
    for t in ["85% Retrieval", "20Q Flask Eval", "Source Citations"]:
        w = chip(draw, x, 70, t, f["chip"])
        x += w + 16

    y = 225
    stage(draw, (90, y, 380, y + 145), "01", "Parse", "Tree-sitter chunks", f["num"], f["stage"], f["stage_sub"])
    stage(draw, (555, y, 845, y + 145), "02", "Retrieve", "Vector + BM25", f["num"], f["stage"], f["stage_sub"])
    stage(draw, (1020, y, 1310, y + 145), "03", "Cite", "Repo/File sources", f["num"], f["stage"], f["stage_sub"])

    arrow(draw, 415, y + 72, 520)
    arrow(draw, 880, y + 72, 985)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT, "PNG", optimize=True)
    print(f"Banner written to {OUTPUT}")

if __name__ == "__main__":
    generate()