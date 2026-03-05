# app.py
import io
import math
from typing import List, Tuple

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

CANVAS_SIZE = (1080, 1080)

# =========================
# Layout (ubah sesuai kebutuhan)
# =========================
LAYOUT = {
    "title_pos": (80, 80),
    "title_font_size": 44,
    "subtitle_pos": (80, 135),
    "subtitle_font_size": 28,

    # unit (centered)
    "unit_center": (700, 620),
    "unit_max_size": (620, 420),  # max w,h

    # spec text block (right side)
    "spec_box": (80, 240, 520, 860),  # x1,y1,x2,y2
    "spec_font_size": 26,
    "spec_line_spacing": 8,

    # selling point logos grid (left bottom)
    "logo_grid_box": (80, 880, 520, 1020),
    "logo_cols": 6,
    "logo_padding": 10,

    # badges optional (top-left small)
    "badge_box": (80, 170, 220, 230),
}

st.set_page_config(page_title="Auto Product Banner 1080x1080", layout="wide")
st.title("Auto Banner Generator (1080×1080)")

# =========================
# Helpers
# =========================
def load_image(uploaded) -> Image.Image:
    img = Image.open(uploaded)
    # Ensure RGBA for compositing
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img

def fit_inside(img: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
    w, h = img.size
    mw, mh = max_size
    scale = min(mw / w, mh / h, 1.0)
    nw, nh = int(w * scale), int(h * scale)
    return img.resize((nw, nh), Image.LANCZOS)

def draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str, box, font, fill=(0,0,0,255), line_spacing=6):
    x1, y1, x2, y2 = box
    max_width = x2 - x1
    max_height = y2 - y1

    words = text.replace("\r", "").split()
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)

    # Render lines until height exceeded
    y = y1
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=font)
        line_h = bbox[3] - bbox[1]
        if y + line_h > y2:
            break
        draw.text((x1, y), line, font=font, fill=fill)
        y += line_h + line_spacing

def paste_center(base: Image.Image, overlay: Image.Image, center_xy: Tuple[int,int]):
    cx, cy = center_xy
    w, h = overlay.size
    x = int(cx - w/2)
    y = int(cy - h/2)
    base.alpha_composite(overlay, (x, y))

def render_logo_grid(base: Image.Image, logos: List[Image.Image], box, cols=6, padding=10):
    if not logos:
        return
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1

    rows = math.ceil(len(logos) / cols)
    cell_w = (bw - padding * (cols - 1)) // cols
    cell_h = (bh - padding * (rows - 1)) // rows if rows else bh

    for idx, logo in enumerate(logos):
        r = idx // cols
        c = idx % cols
        cell_x = x1 + c * (cell_w + padding)
        cell_y = y1 + r * (cell_h + padding)

        fitted = fit_inside(logo, (cell_w, cell_h))
        # center in cell
        px = cell_x + (cell_w - fitted.size[0]) // 2
        py = cell_y + (cell_h - fitted.size[1]) // 2
        base.alpha_composite(fitted, (px, py))

def get_font(size: int):
    # Try common fonts; fallback to default
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size=size)
        except:
            pass
    return ImageFont.load_default()

# =========================
# UI
# =========================
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Input")
    bg_file = st.file_uploader("Upload Background (PNG/JPG)", type=["png", "jpg", "jpeg"])
    unit_file = st.file_uploader("Upload Foto Unit (PNG transparan)", type=["png"])

    logo_files = st.file_uploader(
        "Upload Logo Selling Point (bisa banyak, PNG/JPG)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    title = st.text_input("Judul / Series", "ASUS ROG Zephyrus G16")
    subtitle = st.text_input("Model", "GU605MU")

    spec_text = st.text_area(
        "Text Spesifikasi (satu paragraf / bullet manual)",
        "Intel® Core™ Ultra 7 155H | NVIDIA® GeForce RTX™ 4050\n"
        "16GB LPDDR5X | 1TB PCIe 4.0 NVMe™ M.2 SSD\n"
        "ROG Nebula Display 16-inch 2.5K, 240Hz"
    )

    export_format = st.selectbox("Output", ["PNG", "JPG"])
    jpg_quality = st.slider("JPG Quality", 60, 95, 90) if export_format == "JPG" else None

    generate = st.button("Generate")

with col2:
    st.subheader("Preview / Output")

    if generate:
        if not bg_file or not unit_file:
            st.error("Background dan Foto Unit wajib diupload.")
        else:
            # base canvas
            bg = load_image(bg_file).resize(CANVAS_SIZE, Image.LANCZOS)
            canvas = Image.new("RGBA", CANVAS_SIZE, (255, 255, 255, 255))
            canvas.alpha_composite(bg, (0, 0))

            unit = load_image(unit_file)
            unit = fit_inside(unit, LAYOUT["unit_max_size"])
            paste_center(canvas, unit, LAYOUT["unit_center"])

            # logos
            logos = []
            if logo_files:
                for f in logo_files:
                    logos.append(load_image(f))
            render_logo_grid(
                canvas, logos,
                LAYOUT["logo_grid_box"],
                cols=LAYOUT["logo_cols"],
                padding=LAYOUT["logo_padding"]
            )

            # text
            draw = ImageDraw.Draw(canvas)
            title_font = get_font(LAYOUT["title_font_size"])
            subtitle_font = get_font(LAYOUT["subtitle_font_size"])
            spec_font = get_font(LAYOUT["spec_font_size"])

            draw.text(LAYOUT["title_pos"], title, font=title_font, fill=(0, 0, 0, 255))
            draw.text(LAYOUT["subtitle_pos"], subtitle, font=subtitle_font, fill=(0, 0, 0, 255))

            # draw spec text (wrap by box width)
            # preserve newlines by drawing each paragraph separately
            x1, y1, x2, y2 = LAYOUT["spec_box"]
            y_cursor = y1
            for para in spec_text.split("\n"):
                if not para.strip():
                    y_cursor += LAYOUT["spec_line_spacing"] + 8
                    continue
                draw_wrapped_text(
                    draw, para, (x1, y_cursor, x2, y2),
                    spec_font, fill=(0, 0, 0, 255),
                    line_spacing=LAYOUT["spec_line_spacing"]
                )
                # move cursor roughly one line down; simple approach
                y_cursor += int(LAYOUT["spec_font_size"] * 1.5)

            # show preview
            preview_rgb = canvas.convert("RGB")
            st.image(preview_rgb, caption="Generated Preview", use_container_width=True)

            # export
            buf = io.BytesIO()
            if export_format == "PNG":
                canvas.save(buf, format="PNG")
                mime = "image/png"
                fname = f"{subtitle}_1080.png"
            else:
                preview_rgb.save(buf, format="JPEG", quality=jpg_quality, optimize=True)
                mime = "image/jpeg"
                fname = f"{subtitle}_1080.jpg"

            st.download_button(
                "Download",
                data=buf.getvalue(),
                file_name=fname,
                mime=mime
            )
