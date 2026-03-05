import io
import json
import math
import base64
from copy import deepcopy
from typing import List, Tuple, Optional

import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw, ImageFont


# =========================================================
# 1) INTER EXTRA BOLD (EMBED)
# =========================================================
# Cara isi:
# - Download font Inter ExtraBold .ttf (Inter-ExtraBold.ttf)
# - Convert ke base64:
#     python -c "import base64;print(base64.b64encode(open('Inter-ExtraBold.ttf','rb').read()).decode())"
# - Copy hasilnya ke string di bawah ini.
INTER_EXTRABOLD_TTF_B64 = ""  # <-- TEMPel base64 font di sini


def get_inter_extrabold_font(size: int) -> ImageFont.FreeTypeFont:
    """
    Load Inter ExtraBold dari base64 (tanpa file assets).
    Kalau base64 kosong / gagal, fallback ke DejaVu.
    """
    if INTER_EXTRABOLD_TTF_B64.strip():
        try:
            font_bytes = base64.b64decode(INTER_EXTRABOLD_TTF_B64.encode("utf-8"))
            return ImageFont.truetype(io.BytesIO(font_bytes), size=size)
        except Exception:
            pass

    # Fallback (kalau base64 belum diisi)
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue

    return ImageFont.load_default()


# =========================================================
# 2) DEFAULT TEMPLATE (NO FILE NEEDED)
# =========================================================
DEFAULT_LAYOUT = {
    "canvas_w": 1080,
    "canvas_h": 1080,

    "title_pos": [80, 120],
    "title_font_size": 44,

    "model_pos": [80, 180],
    "model_font_size": 32,

    "spec_box": [80, 300, 520, 620],
    "spec_font_size": 30,
    "spec_line_spacing": 10,

    "unit_box": [480, 360, 1040, 860],

    "logo_grid_box": [80, 820, 700, 1000],
    "logo_cols": 7,
    "logo_padding": 18
}


# =========================================================
# 3) RENDER HELPERS
# =========================================================
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
    paste_into_box(canvas, ensure_rgba(unit), tuple(layout["unit_box"]))

    # Logos
    render_logo_grid(
        canvas,
        [ensure_rgba(l) for l in logos],
        tuple(layout["logo_grid_box"]),
        cols=int(layout["logo_cols"]),
        padding=int(layout["logo_padding"])
    )

    # Text
    draw = ImageDraw.Draw(canvas)
    title_font = get_inter_extrabold_font(int(layout["title_font_size"]))
    model_font = get_inter_extrabold_font(int(layout["model_font_size"]))
    spec_font = get_inter_extrabold_font(int(layout["spec_font_size"]))

    draw.text(tuple(layout["title_pos"]), title, font=title_font, fill=(0, 0, 0, 255))
    draw.text(tuple(layout["model_pos"]), model, font=model_font, fill=(0, 0, 0, 255))

    draw_wrapped_text(
        draw,
        spec_text,
        tuple(layout["spec_box"]),
        spec_font,
        fill=(0, 0, 0, 255),
        line_spacing=int(layout["spec_line_spacing"])
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


def ensure_canvas_bg(img: Image.Image) -> Image.Image:
    """
    FIX streamlit-drawable-canvas: pastikan format image tidak None.
    """
    img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Image.open(buf)


def clamp_box(box, w, h):
    x1, y1, x2, y2 = box
    x1 = max(0, min(int(x1), w))
    x2 = max(0, min(int(x2), w))
    y1 = max(0, min(int(y1), h))
    y2 = max(0, min(int(y2), h))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    if x2 == x1:
        x2 = min(w, x1 + 1)
    if y2 == y1:
        y2 = min(h, y1 + 1)
    return [x1, y1, x2, y2]


# =========================================================
# 4) STREAMLIT UI
# =========================================================
st.set_page_config(page_title="Auto Banner Generator 1080×1080", layout="wide")
st.title("Auto Banner Generator (1080×1080) — Upload → Edit Layout → Export")

if "layout" not in st.session_state:
    st.session_state.layout = deepcopy(DEFAULT_LAYOUT)

layout = st.session_state.layout
canvas_w = int(layout["canvas_w"])
canvas_h = int(layout["canvas_h"])

tab1, tab2 = st.tabs(["Generate", "Layout Editor (Drag Kotak)"])

# -------- TAB 1
with tab1:
    left, right = st.columns([1, 1])

    with left:
        st.subheader("Input")
        bg_file = st.file_uploader("Background (PNG/JPG)", type=["png", "jpg", "jpeg"])
        unit_file = st.file_uploader("Foto Unit (PNG transparan)", type=["png"])
        logo_files = st.file_uploader(
            "Logo Selling Point (boleh banyak, PNG/JPG)",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True
        )

        title = st.text_input("Judul / Series", "ASUS ROG Zephyrus G16")
        model = st.text_input("Model", "GU605MU")
        spec_text = st.text_area(
            "Text Spesifikasi (boleh multi-line)",
            "Intel® Core™ Ultra 7 155H | NVIDIA® GeForce RTX™ 4050\n"
            "16GB LPDDR5X | 1TB PCIe 4.0 NVMe™ M.2 SSD\n"
            "ROG Nebula Display 16-inch 2.5K, 240Hz",
            height=130
        )

        st.markdown("---")
        st.subheader("Export")
        fmt = st.selectbox("Format", ["PNG", "JPG"])
        jpg_quality = st.slider("JPG Quality", 60, 95, 90) if fmt == "JPG" else 90

        generate = st.button("Generate")

        if not INTER_EXTRABOLD_TTF_B64.strip():
            st.warning("Inter ExtraBold belum di-embed. App masih jalan pakai font fallback (DejaVu).")

    with right:
        st.subheader("Preview / Output")

        if generate:
            if not bg_file or not unit_file:
                st.error("Background dan Foto Unit wajib diupload.")
            else:
                bg = load_image(bg_file)
                unit = load_image(unit_file)
                logos = [load_image(lf) for lf in (logo_files or [])]

                out = render_banner(
                    background=bg,
                    unit=unit,
                    logos=logos,
                    title=title,
                    model=model,
                    spec_text=spec_text,
                    layout=layout
                )

                st.image(out.convert("RGB"), use_container_width=True)

                data, mime, ext = export_image(out, fmt=fmt, jpg_quality=jpg_quality)
                filename = f"{model}_{canvas_w}x{canvas_h}.{ext}"
                st.download_button("Download", data=data, file_name=filename, mime=mime)

        st.caption("Tip: Kalau posisi belum pas, buka tab Layout Editor untuk geser area unit/spec/logo pakai drag kotak.")

# -------- TAB 2
with tab2:
    st.subheader("Layout Editor — Drag Kotak Area")

    colA, colB = st.columns([1, 1])

    with colA:
        bg_for_editor = st.file_uploader(
            "Background untuk editor (PNG/JPG)",
            type=["png", "jpg", "jpeg"],
            key="bg_editor"
        )

        if bg_for_editor:
            raw = load_image(bg_for_editor).resize((canvas_w, canvas_h), Image.LANCZOS)
            bg_img = ensure_canvas_bg(raw)
        else:
            blank = Image.new("RGB", (canvas_w, canvas_h), (245, 245, 245))
            bg_img = ensure_canvas_bg(blank)

        st.markdown("### Gambar kotak (Rect)")

        canvas_result = st_canvas(
            fill_color="rgba(0, 0, 0, 0)",
            stroke_width=3,
            stroke_color="rgba(255, 0, 0, 0.85)",
            background_image=bg_img,
            update_streamlit=True,
            height=canvas_h,
            width=canvas_w,
            drawing_mode="rect",
            key="canvas_layout",
        )

    with colB:
        st.markdown("### Setting Grid")
        logo_cols = st.slider("Logo cols", 3, 12, int(layout.get("logo_cols", 7)))
        logo_padding = st.slider("Logo padding", 0, 40, int(layout.get("logo_padding", 18)))

        st.markdown("### Font Size")
        title_size = st.slider("Title font size", 20, 90, int(layout.get("title_font_size", 44)))
        model_size = st.slider("Model font size", 16, 70, int(layout.get("model_font_size", 32)))
        spec_size = st.slider("Spec font size", 16, 70, int(layout.get("spec_font_size", 30)))
        spec_spacing = st.slider("Spec line spacing", 0, 30, int(layout.get("spec_line_spacing", 10)))

        st.markdown("### Posisi Title/Model (manual)")
        tx = st.number_input("Title X", 0, canvas_w, int(layout.get("title_pos", [80, 120])[0]))
        ty = st.number_input("Title Y", 0, canvas_h, int(layout.get("title_pos", [80, 120])[1]))
        mx = st.number_input("Model X", 0, canvas_w, int(layout.get("model_pos", [80, 180])[0]))
        my = st.number_input("Model Y", 0, canvas_h, int(layout.get("model_pos", [80, 180])[1]))

        rects = []
        if canvas_result.json_data and "objects" in canvas_result.json_data:
            for obj in canvas_result.json_data["objects"]:
                if obj.get("type") == "rect":
                    left = obj.get("left", 0)
                    top = obj.get("top", 0)
                    width = obj.get("width", 1) * obj.get("scaleX", 1)
                    height = obj.get("height", 1) * obj.get("scaleY", 1)
                    rects.append([left, top, left + width, top + height])

        st.info(
            "Urutan kotak:\n"
            "1) UNIT BOX\n"
            "2) SPEC BOX\n"
            "3) LOGO GRID BOX\n\n"
            f"Jumlah kotak terdeteksi: {len(rects)}"
        )

        if st.button("Apply Layout dari kotak"):
            new_layout = deepcopy(layout)
            new_layout["logo_cols"] = int(logo_cols)
            new_layout["logo_padding"] = int(logo_padding)
            new_layout["title_font_size"] = int(title_size)
            new_layout["model_font_size"] = int(model_size)
            new_layout["spec_font_size"] = int(spec_size)
            new_layout["spec_line_spacing"] = int(spec_spacing)
            new_layout["title_pos"] = [int(tx), int(ty)]
            new_layout["model_pos"] = [int(mx), int(my)]

            if len(rects) >= 1:
                new_layout["unit_box"] = clamp_box(rects[0], canvas_w, canvas_h)
            if len(rects) >= 2:
                new_layout["spec_box"] = clamp_box(rects[1], canvas_w, canvas_h)
            if len(rects) >= 3:
                new_layout["logo_grid_box"] = clamp_box(rects[2], canvas_w, canvas_h)

            st.session_state.layout = new_layout
            st.success("Layout diterapkan. Balik ke tab Generate untuk test.")

        st.markdown("---")
        st.markdown("### Export / Import Template JSON")
        colx, coly = st.columns(2)

        with colx:
            if st.button("Download Template JSON"):
                blob = json.dumps(st.session_state.layout, ensure_ascii=False, indent=2).encode("utf-8")
                st.download_button("Download now", data=blob, file_name="template.json", mime="application/json")

        with coly:
            uploaded_tpl = st.file_uploader("Upload Template JSON", type=["json"], key="tpl_upload")
            if uploaded_tpl:
                tpl = json.load(uploaded_tpl)
                st.session_state.layout = tpl
                st.success("Template loaded dari JSON.")
