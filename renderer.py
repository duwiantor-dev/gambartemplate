import io
import math
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

DEFAULT_FONT_PATH = "assets/fonts/Inter-ExtraBold.ttf"


def ensure_rgba(img: Image.Image) -> Image.Image:
    return img.convert("RGBA") if img.mode != "RGBA" else img


def load_image(uploaded_file) -> Image.Image:
    img = Image.open(uploaded_file)
    return ensure_rgba(img)


def fit_inside(img: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
    w, h = img.size
    mw, mh = max_size
    scale = min(mw / w, mh / h, 1.0)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return img.resize((nw, nh), Image.LANCZOS)


def get_font(size: int, font_path: Optional[str] = None):
    fp = font_path or DEFAULT_FONT_PATH
    try:
        return ImageFont.truetype(fp, size=size)
    except Exception:
        # fallback system
        for path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]:
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
        return ImageFont.load_default()


def draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str, box, font, fill=(0, 0, 0, 255), line_spacing=8):
    x1, y1, x2, y2 = box
    max_width = x2 - x1

    paragraphs = text.replace("\r", "").split("\n")
    y = y1

    for para in paragraphs:
        para = para.strip()
        if not para:
            y += int(font.size * 0.6)
            continue

        words = para.split()
        lines = []
        cur = ""

        for w in words:
            test = (cur + " " + w).strip()
            if draw.textlength(test, font=font) <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)

        for ln in lines:
            bbox = draw.textbbox((0, 0), ln, font=font)
            line_h = bbox[3] - bbox[1]
            if y + line_h > y2:
                return
            draw.text((x1, y), ln, font=font, fill=fill)
            y += line_h + line_spacing

        y += int(font.size * 0.3)


def paste_into_box(base: Image.Image, overlay: Image.Image, box):
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    fitted = fit_inside(overlay, (bw, bh))
    px = x1 + (bw - fitted.size[0]) // 2
    py = y1 + (bh - fitted.size[1]) // 2
    base.alpha_composite(fitted, (px, py))


def render_logo_grid(base: Image.Image, logos: List[Image.Image], box, cols=7, padding=16):
    if not logos:
        return
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1

    cols = max(1, int(cols))
    rows = math.ceil(len(logos) / cols)

    cell_w = (bw - padding * (cols - 1)) // cols
    cell_h = (bh - padding * (rows - 1)) // max(1, rows)

    for idx, logo in enumerate(logos):
        r = idx // cols
        c = idx % cols
        cx = x1 + c * (cell_w + padding)
        cy = y1 + r * (cell_h + padding)

        fitted = fit_inside(logo, (cell_w, cell_h))
        px = cx + (cell_w - fitted.size[0]) // 2
        py = cy + (cell_h - fitted.size[1]) // 2
        base.alpha_composite(fitted, (px, py))


def render_banner(background, unit, logos, title, model, spec_text, layout: dict):
    canvas_w = int(layout.get("canvas_w", 1080))
    canvas_h = int(layout.get("canvas_h", 1080))

    bg = ensure_rgba(background).resize((canvas_w, canvas_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
    canvas.alpha_composite(bg, (0, 0))

    # Unit
    unit_box = tuple(layout.get("unit_box", [480, 360, 1040, 860]))
    paste_into_box(canvas, ensure_rgba(unit), unit_box)

    # Logos
    logo_box = tuple(layout.get("logo_grid_box", [80, 820, 700, 1000]))
    render_logo_grid(
        canvas,
        [ensure_rgba(l) for l in logos],
        logo_box,
        cols=int(layout.get("logo_cols", 7)),
        padding=int(layout.get("logo_padding", 18))
    )

    # Text
    draw = ImageDraw.Draw(canvas)
    title_font = get_font(int(layout.get("title_font_size", 44)))
    model_font = get_font(int(layout.get("model_font_size", 32)))
    spec_font = get_font(int(layout.get("spec_font_size", 30)))

    draw.text(tuple(layout.get("title_pos", [80, 120])), title, font=title_font, fill=(0, 0, 0, 255))
    draw.text(tuple(layout.get("model_pos", [80, 180])), model, font=model_font, fill=(0, 0, 0, 255))

    spec_box = tuple(layout.get("spec_box", [80, 300, 520, 620]))
    draw_wrapped_text(
        draw,
        spec_text,
        spec_box,
        spec_font,
        fill=(0, 0, 0, 255),
        line_spacing=int(layout.get("spec_line_spacing", 10))
    )

    return canvas


def export_image(img_rgba: Image.Image, fmt: str = "PNG", jpg_quality: int = 90):
    buf = io.BytesIO()
    fmt = fmt.upper().strip()
    if fmt in ("JPG", "JPEG"):
        rgb = img_rgba.convert("RGB")
        rgb.save(buf, format="JPEG", quality=jpg_quality, optimize=True)
        return buf.getvalue(), "image/jpeg", "jpg"
    img_rgba.save(buf, format="PNG")
    return buf.getvalue(), "image/png", "png"
