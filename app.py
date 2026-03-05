import json
import os
from copy import deepcopy

import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image

from renderer import load_image, render_banner, export_image, ensure_rgba

TEMPLATE_DIR = "templates"
DEFAULT_TEMPLATE_PATH = os.path.join(TEMPLATE_DIR, "default.json")


def load_template(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_template(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clamp_box(box, w, h):
    x1, y1, x2, y2 = box
    x1 = max(0, min(int(x1), w))
    x2 = max(0, min(int(x2), w))
    y1 = max(0, min(int(y1), h))
    y2 = max(0, min(int(y2), h))
    # ensure proper order
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    # avoid zero
    if x2 == x1:
        x2 = min(w, x1 + 1)
    if y2 == y1:
        y2 = min(h, y1 + 1)
    return [x1, y1, x2, y2]


st.set_page_config(page_title="Auto Banner Generator 1080×1080", layout="wide")
st.title("Auto Banner Generator (1080×1080) — Upload → Edit Layout → Export")

# Load default template into session
if "layout" not in st.session_state:
    st.session_state.layout = load_template(DEFAULT_TEMPLATE_PATH)

layout = st.session_state.layout
canvas_w = int(layout.get("canvas_w", 1080))
canvas_h = int(layout.get("canvas_h", 1080))

tab1, tab2 = st.tabs(["Generate", "Layout Editor (Drag Kotak)"])

# =========================
# TAB 1: GENERATE
# =========================
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

        # Optional font
        font_file = st.file_uploader("Font TTF (optional, untuk gaya konsisten)", type=["ttf"], key="font_ttf")
        font_path = None
        if font_file:
            os.makedirs("assets/fonts", exist_ok=True)
            font_path = os.path.join("assets/fonts", font_file.name)
            with open(font_path, "wb") as f:
                f.write(font_file.getbuffer())

        generate = st.button("Generate")

    with right:
        st.subheader("Preview / Output")

        if generate:
            if not bg_file or not unit_file:
                st.error("Background dan Foto Unit wajib diupload.")
            else:
                bg = load_image(bg_file)
                unit = load_image(unit_file)

                logos = []
                if logo_files:
                    for lf in logo_files:
                        logos.append(load_image(lf))

                out = render_banner(
                    background=bg,
                    unit=unit,
                    logos=logos,
                    title=title,
                    model=model,
                    spec_text=spec_text,
                    layout=layout,
                    font_path=font_path
                )

                preview = out.convert("RGB")
                st.image(preview, use_container_width=True)

                data, mime, ext = export_image(out, fmt=fmt, jpg_quality=jpg_quality)
                filename = f"{model}_{canvas_w}x{canvas_h}.{ext}"

                st.download_button(
                    "Download",
                    data=data,
                    file_name=filename,
                    mime=mime
                )

        st.markdown("---")
        st.caption("Tip: Kalau posisi belum pas, buka tab **Layout Editor** untuk geser area unit/spec/logo pakai drag kotak.")

# =========================
# TAB 2: LAYOUT EDITOR
# =========================
with tab2:
    st.subheader("Layout Editor — Drag Kotak Area")

    st.write(
        "Cara pakai:\n"
        "1) Upload background (biar ada visual).\n"
        "2) Gambar 3 kotak: **UNIT**, **SPEC**, **LOGO GRID**.\n"
        "3) Klik **Apply** untuk menyimpan layout ke session.\n"
        "4) (Optional) Save template ke file JSON."
    )

    colA, colB = st.columns([1, 1])

    with colA:
        bg_for_editor = st.file_uploader("Background untuk editor (PNG/JPG)", type=["png", "jpg", "jpeg"], key="bg_editor")

        if bg_for_editor:
            bg_img = load_image(bg_for_editor).resize((canvas_w, canvas_h))
        else:
            # fallback: blank
            bg_img = Image.new("RGBA", (canvas_w, canvas_h), (245, 245, 245, 255))

        st.markdown("### Gambar kotak (Rect)")

        canvas_result = st_canvas(
            fill_color="rgba(0, 0, 0, 0)",
            stroke_width=3,
            stroke_color="rgba(255, 0, 0, 0.8)",
            background_image=bg_img.convert("RGB"),
            update_streamlit=True,
            height=canvas_h,
            width=canvas_w,
            drawing_mode="rect",
            key="canvas_layout",
        )

    with colB:
        st.markdown("### Setting Text & Grid (opsional)")

        # Quick sliders for text sizes
        title_size = st.slider("Title font size", 20, 80, int(layout.get("title_font_size", 44)))
        model_size = st.slider("Model font size", 16, 60, int(layout.get("model_font_size", 32)))
        spec_size = st.slider("Spec font size", 16, 60, int(layout.get("spec_font_size", 30)))
        spec_spacing = st.slider("Spec line spacing", 0, 24, int(layout.get("spec_line_spacing", 10)))

        logo_cols = st.slider("Logo cols", 3, 12, int(layout.get("logo_cols", 7)))
        logo_padding = st.slider("Logo padding", 0, 40, int(layout.get("logo_padding", 18)))

        st.markdown("---")
        st.markdown("### Posisi Title/Model (manual)")
        tx = st.number_input("Title X", 0, canvas_w, int(layout.get("title_pos", [80, 120])[0]))
        ty = st.number_input("Title Y", 0, canvas_h, int(layout.get("title_pos", [80, 120])[1]))
        mx = st.number_input("Model X", 0, canvas_w, int(layout.get("model_pos", [80, 180])[0]))
        my = st.number_input("Model Y", 0, canvas_h, int(layout.get("model_pos", [80, 180])[1]))

        st.markdown("---")
        st.markdown("### Apply / Save / Load")

        # Parse rectangles from canvas
        rects = []
        if canvas_result.json_data and "objects" in canvas_result.json_data:
            for obj in canvas_result.json_data["objects"]:
                if obj.get("type") == "rect":
                    left = obj.get("left", 0)
                    top = obj.get("top", 0)
                    width = obj.get("width", 1) * obj.get("scaleX", 1)
                    height = obj.get("height", 1) * obj.get("scaleY", 1)
                    x1, y1 = left, top
                    x2, y2 = left + width, top + height
                    rects.append([x1, y1, x2, y2])

        st.info(
            "Urutan kotak yang dipakai:\n"
            "1) Kotak pertama = UNIT BOX\n"
            "2) Kotak kedua = SPEC BOX\n"
            "3) Kotak ketiga = LOGO GRID BOX\n\n"
            f"Jumlah kotak terdeteksi: {len(rects)}"
        )

        apply_btn = st.button("Apply Layout dari kotak")

        if apply_btn:
            new_layout = deepcopy(layout)
            new_layout["title_font_size"] = int(title_size)
            new_layout["model_font_size"] = int(model_size)
            new_layout["spec_font_size"] = int(spec_size)
            new_layout["spec_line_spacing"] = int(spec_spacing)
            new_layout["logo_cols"] = int(logo_cols)
            new_layout["logo_padding"] = int(logo_padding)
            new_layout["title_pos"] = [int(tx), int(ty)]
            new_layout["model_pos"] = [int(mx), int(my)]

            if len(rects) >= 1:
                new_layout["unit_box"] = clamp_box(rects[0], canvas_w, canvas_h)
            if len(rects) >= 2:
                new_layout["spec_box"] = clamp_box(rects[1], canvas_w, canvas_h)
            if len(rects) >= 3:
                new_layout["logo_grid_box"] = clamp_box(rects[2], canvas_w, canvas_h)

            st.session_state.layout = new_layout
            st.success("Layout diterapkan ke session. Coba balik ke tab Generate.")

        st.markdown("---")
        # Save template
        template_name = st.text_input("Nama template untuk disimpan", "my_template.json")
        save_btn = st.button("Save Template JSON")

        if save_btn:
            path = os.path.join(TEMPLATE_DIR, template_name)
            save_template(path, st.session_state.layout)
            st.success(f"Template tersimpan: {path}")

        # Load template
        st.markdown("### Load template yang ada")
        if os.path.isdir(TEMPLATE_DIR):
            files = [f for f in os.listdir(TEMPLATE_DIR) if f.lower().endswith(".json")]
        else:
            files = []

        chosen = st.selectbox("Pilih template", files if files else ["default.json"])
        load_btn = st.button("Load Template")

        if load_btn:
            path = os.path.join(TEMPLATE_DIR, chosen)
            if os.path.exists(path):
                st.session_state.layout = load_template(path)
                st.success(f"Loaded: {path}")
            else:
                st.error("File template tidak ditemukan.")
