import io
import math
import re
import zipfile
from dataclasses import dataclass
from typing import List

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CANVAS_SIZE = 1080
MAX_BADGES = 5
PHOTO_BOX = (50, 165, 585, 780)
BADGE_AREA = (520, 160, 850, 350)
TITLE_AREA = (740, 120, 1030, 310)
SPEC_AREA = (705, 345, 1035, 900)
ACCENT = (214, 27, 143)
TEXT_DARK = (20, 25, 38)
WHITE = (255, 255, 255)

POINT_SELLING_DB = [
    {"keywords": ["RTX5090"], "label": "RTX 5090", "priority": 100},
    {"keywords": ["RTX5080"], "label": "RTX 5080", "priority": 99},
    {"keywords": ["RTX5070"], "label": "RTX 5070", "priority": 98},
    {"keywords": ["RTX5060"], "label": "RTX 5060", "priority": 97},
    {"keywords": ["RTX5050"], "label": "RTX 5050", "priority": 96},
    {"keywords": ["RTX4070"], "label": "RTX 4070", "priority": 95},
    {"keywords": ["RTX4060"], "label": "RTX 4060", "priority": 94},
    {"keywords": ["RTX4050"], "label": "RTX 4050", "priority": 93},
    {"keywords": ["RTX3050"], "label": "RTX 3050", "priority": 92},
    {"keywords": ["RTX2050"], "label": "RTX 2050", "priority": 91},
    {"keywords": ["RX7600S", "RX 7600S"], "label": "Radeon RX 7600S", "priority": 90},
    {"keywords": ["RX7700S", "RX 7700S"], "label": "Radeon RX 7700S", "priority": 89},
    {"keywords": ["ULTRA 9", "CORE ULTRA 9"], "label": "Core Ultra 9", "priority": 88},
    {"keywords": ["ULTRA 7", "CORE ULTRA 7"], "label": "Core Ultra 7", "priority": 87},
    {"keywords": ["ULTRA 5", "CORE ULTRA 5"], "label": "Core Ultra 5", "priority": 86},
    {"keywords": ["I9", "CORE I9"], "label": "Intel Core i9", "priority": 85},
    {"keywords": ["I7", "CORE I7"], "label": "Intel Core i7", "priority": 84},
    {"keywords": ["I5", "CORE I5"], "label": "Intel Core i5", "priority": 83},
    {"keywords": ["RYZEN 9"], "label": "Ryzen 9", "priority": 82},
    {"keywords": ["RYZEN 7"], "label": "Ryzen 7", "priority": 81},
    {"keywords": ["RYZEN 5"], "label": "Ryzen 5", "priority": 80},
    {"keywords": ["32GB"], "label": "32GB RAM", "priority": 79},
    {"keywords": ["24GB"], "label": "24GB RAM", "priority": 78},
    {"keywords": ["16GB"], "label": "16GB RAM", "priority": 77},
    {"keywords": ["8GB"], "label": "8GB RAM", "priority": 76},
    {"keywords": ["2TB"], "label": "2TB SSD", "priority": 75},
    {"keywords": ["1TB"], "label": "1TB SSD", "priority": 74},
    {"keywords": ["512GB"], "label": "512GB SSD", "priority": 73},
    {"keywords": ["OLED"], "label": "OLED Display", "priority": 72},
    {"keywords": ["2.8K"], "label": "2.8K Display", "priority": 71},
    {"keywords": ["2.5K"], "label": "2.5K Display", "priority": 70},
    {"keywords": ["165HZ", "165 HZ"], "label": "165Hz", "priority": 69},
    {"keywords": ["180HZ", "180 HZ"], "label": "180Hz", "priority": 68},
    {"keywords": ["240HZ", "240 HZ"], "label": "240Hz", "priority": 67},
    {"keywords": ["144HZ", "144 HZ"], "label": "144Hz", "priority": 66},
    {"keywords": ["120HZ", "120 HZ"], "label": "120Hz", "priority": 65},
    {"keywords": ["W11", "WINDOWS 11"], "label": "Windows 11", "priority": 64},
    {"keywords": ["OHS"], "label": "Office H&S", "priority": 63},
    {"keywords": ["M365B", "M365"], "label": "Microsoft 365", "priority": 62},
    {"keywords": ["ADP"], "label": "ADP", "priority": 61},
    {"keywords": ["PEN"], "label": "Stylus Support", "priority": 60},
    {"keywords": ["TOUCH"], "label": "Touchscreen", "priority": 59},
    {"keywords": ["FREE DOS"], "label": "Free DOS", "priority": 58},
    {"keywords": ["NEBULA"], "label": "Nebula Display", "priority": 57},
]

TITLE_STOPWORDS = {
    "RTX", "GTX", "RX", "16GB", "32GB", "24GB", "8GB", "512GB", "1TB", "2TB",
    "W11", "OHS", "M365", "M365B", "15.6", "16.0", "16", "14.0", "14", "13.3",
    "120HZ", "144HZ", "165HZ", "180HZ", "240HZ"
}

SAMPLE_SPECS = """ACER NITRO V 16S RYZEN 7 260 RTX5060 8GB/16GB 512GB W11+OHS+M365B 16.0WQXGA 180HZ 100SRGB 2Y+ADP BLK -41.R70Y
LENOVO YOGA SLIM 7 14 TOUCH ULTRA 5 125H 16GB 512GB W11+OHS+M365B 14.0WUXGA OLED EVO 3Y PREM+3ADP GRY -A81D
MSI THIN 15 I5 13420H RTX3050 4GB 8GB 512GB W11 15.6FHD 144HZ BLK"""


@dataclass
class ProductItem:
    index: int
    raw: str
    title: str
    selling_points: List[str]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").upper()).strip()


def sanitize_filename(value: str) -> str:
    value = re.sub(r'[\\/:*?"<>|]+', '', str(value or 'output'))
    value = re.sub(r'\s+', '-', value).strip('-')
    return value[:120] or 'output'


def extract_title(spec: str) -> str:
    clean = normalize_text(spec)
    tokens = clean.split()
    result = []
    for token in tokens:
        if token in TITLE_STOPWORDS:
            break
        if re.match(r'^(RTX|GTX|RX)\d+', token):
            break
        if re.match(r'^\d+(GB|TB)$', token):
            break
        if re.match(r'^\d+(\.\d+)?(HZ)?$', token) and len(result) >= 2:
            break
        result.append(token)
        if len(result) >= 7:
            break
    return ' '.join(result).strip() or clean[:40]


def detect_selling_points(spec: str) -> List[str]:
    text = normalize_text(spec)
    matches = []
    for item in POINT_SELLING_DB:
        if any(normalize_text(k) in text for k in item['keywords']):
            matches.append(item)
    matches.sort(key=lambda x: x['priority'], reverse=True)
    labels = []
    for item in matches:
        if item['label'] not in labels:
            labels.append(item['label'])
        if len(labels) >= MAX_BADGES:
            break
    return labels


def parse_spec_lines(text: str) -> List[ProductItem]:
    lines = [line.strip() for line in str(text or '').splitlines() if line.strip()]
    return [
        ProductItem(
            index=i,
            raw=line,
            title=extract_title(line),
            selling_points=detect_selling_points(line),
        )
        for i, line in enumerate(lines)
    ]


def read_specs_from_excel(uploaded_file) -> str:
    if uploaded_file is None:
        return ''
    name = uploaded_file.name.lower()
    if name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    if df.empty:
        return ''

    preferred = None
    for col in df.columns:
        if normalize_text(col) == 'SPESIFIKASI':
            preferred = col
            break

    if preferred is not None:
        series = df[preferred]
    else:
        series = df.iloc[:, 0]

    lines = [str(v).strip() for v in series.fillna('').tolist() if str(v).strip()]
    return '\n'.join(lines)


def get_font(size: int, bold: bool = False):
    candidates = [
        '/mnt/data/Inter-ExtraBold.otf',
    ]
    if bold:
        candidates += [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
        ]
    candidates += [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def fit_image_contain(image: Image.Image, box):
    x1, y1, x2, y2 = box
    box_w = x2 - x1
    box_h = y2 - y1
    src_w, src_h = image.size
    ratio = min(box_w / src_w, box_h / src_h)
    new_size = (max(1, int(src_w * ratio)), max(1, int(src_h * ratio)))
    resized = image.resize(new_size, Image.LANCZOS)
    pos_x = x1 + (box_w - new_size[0]) // 2
    pos_y = y1 + (box_h - new_size[1]) // 2
    return resized, (pos_x, pos_y)


def wrap_text_by_width(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int):
    words = str(text or '').split()
    lines = []
    current = ''
    for word in words:
        candidate = word if not current else f'{current} {word}'
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if width <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines - 1:
                break
    if current and len(lines) < max_lines:
        lines.append(current)

    if len(lines) == max_lines and ' '.join(words) != ' '.join(lines):
        while lines[-1] and draw.textbbox((0, 0), lines[-1] + '...', font=font)[2] > max_width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += '...'
    return lines


def fit_font_size(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int = 16, bold: bool = True):
    size = start_size
    font = get_font(size, bold=bold)
    while size > min_size and draw.textbbox((0, 0), text, font=font)[2] > max_width:
        size -= 2
        font = get_font(size, bold=bold)
    return font, size


def draw_centered_lines(draw: ImageDraw.ImageDraw, lines, box, font, fill, line_gap=8):
    x1, y1, x2, y2 = box
    heights = []
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + line_gap * max(0, len(lines) - 1)
    y = y1 + ((y2 - y1) - total_h) / 2
    for i, line in enumerate(lines):
        x = x1 + ((x2 - x1) - widths[i]) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += heights[i] + line_gap


def rounded_rectangle(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_badges(base: Image.Image, labels: List[str]):
    if not labels:
        return
    draw = ImageDraw.Draw(base)
    x1, y1, x2, _ = BADGE_AREA
    badge_font = get_font(28, bold=True)
    col_w = 155
    badge_h = 56
    gap_x = 12
    gap_y = 12

    for i, label in enumerate(labels[:MAX_BADGES]):
        row = i // 2
        col = i % 2
        bx1 = x1 + col * (col_w + gap_x)
        by1 = y1 + row * (badge_h + gap_y)
        bx2 = bx1 + col_w
        by2 = by1 + badge_h
        rounded_rectangle(draw, (bx1, by1, bx2, by2), 16, fill=(255, 255, 255, 235), outline=(255, 255, 255, 160), width=2)
        text_bbox = draw.textbbox((0, 0), label, font=badge_font)
        tx = bx1 + (col_w - (text_bbox[2] - text_bbox[0])) / 2
        ty = by1 + (badge_h - (text_bbox[3] - text_bbox[1])) / 2 - 2
        draw.text((tx, ty), label, font=badge_font, fill=TEXT_DARK)


def render_card(background: Image.Image, product_photo: Image.Image, item: ProductItem) -> Image.Image:
    base = background.convert('RGBA').resize((CANVAS_SIZE, CANVAS_SIZE), Image.LANCZOS)

    photo = product_photo.convert('RGBA')
    photo_box = (165, 455, 920, 1025)
    contained, (px, py) = fit_image_contain(photo, photo_box)
    base.alpha_composite(contained, (px, py))

    overlay = Image.new('RGBA', base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    clean = normalize_text(item.raw)
    model_match = re.search(r'\b([A-Z]{1,4}\d{3,}[A-Z0-9.-]*)\b', clean)
    model_text = model_match.group(1) if model_match else ''

    title_text = item.title.strip()
    if model_text and model_text in title_text:
        title_text = title_text.replace(model_text, '').strip()
    if not title_text:
        title_text = item.title.strip()

    # Fixed banner text positions based on uploaded background
    title_box = (175, 120, 1015, 225)
    title_font, _ = fit_font_size(draw, title_text, title_box[2] - title_box[0] - 40, 56, 28, True)
    title_lines = wrap_text_by_width(draw, title_text, title_font, title_box[2] - title_box[0] - 40, 2)
    draw_centered_lines(draw, title_lines, title_box, title_font, (255, 255, 255), line_gap=6)

    model_display = model_text or item.title.split()[-1]
    model_box = (420, 236, 782, 340)
    model_font, _ = fit_font_size(draw, model_display, model_box[2] - model_box[0] - 24, 54, 26, True)
    draw_centered_lines(draw, [model_display], model_box, model_font, (245, 235, 0), line_gap=0)

    spec_box = (110, 300, 1090, 420)
    spec_font = get_font(31, bold=True)
    spec_lines = wrap_text_by_width(draw, item.raw, spec_font, spec_box[2] - spec_box[0] - 20, 2)
    if len(spec_lines) > 2:
        spec_font = get_font(27, bold=True)
        spec_lines = wrap_text_by_width(draw, item.raw, spec_font, spec_box[2] - spec_box[0] - 20, 2)
    draw_centered_lines(draw, spec_lines, spec_box, spec_font, (0, 0, 0), line_gap=8)

    footer_font = get_font(16, bold=True)
    footer_text = '1080 x 1080'
    fb = draw.textbbox((0, 0), footer_text, font=footer_font)
    fw = fb[2] - fb[0] + 34
    fh = 34
    fx = 900
    fy = 1018
    rounded_rectangle(draw, (fx, fy, fx + fw, fy + fh), 18, fill=(27, 33, 49, 230))
    draw.text((fx + 17, fy + 8), footer_text, font=footer_font, fill=WHITE)

    composed = Image.alpha_composite(base, overlay)
    return composed.convert('RGB')


def image_to_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    return buf.getvalue()


def build_zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, payload in files:
            zf.writestr(filename, payload)
    buf.seek(0)
    return buf.getvalue()


def main():
    st.set_page_config(page_title='Auto Product Image Generator', layout='wide')
    st.title('Auto Product Image Generator')
    st.caption('Upload 1 background, upload foto produk sesuai urutan, lalu paste spesifikasi atau import Excel.')

    if 'spec_text' not in st.session_state:
        st.session_state.spec_text = SAMPLE_SPECS

    left, right = st.columns([1, 1.5])

    with left:
        bg_file = st.file_uploader('Upload background', type=['png', 'jpg', 'jpeg'])
        photo_files = st.file_uploader('Upload foto produk', type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True)
        excel_file = st.file_uploader('Upload Excel bulk', type=['xlsx', 'xls', 'csv'])

        if excel_file is not None:
            try:
                st.session_state.spec_text = read_specs_from_excel(excel_file)
                st.success('Excel berhasil dibaca.')
            except Exception as exc:
                st.error(f'Gagal membaca Excel: {exc}')

        st.session_state.spec_text = st.text_area(
            'Paste Spesifikasi',
            value=st.session_state.spec_text,
            height=260,
            help='1 baris = 1 produk. Urutan harus sama dengan urutan foto.',
        )

    items = parse_spec_lines(st.session_state.spec_text)

    with right:
        c1, c2, c3 = st.columns(3)
        c1.metric('Jumlah spesifikasi', len(items))
        c2.metric('Jumlah foto', len(photo_files) if photo_files else 0)
        c3.metric('Mode output', 'ZIP' if len(items) > 1 or (photo_files and len(photo_files) > 1) else 'PNG')

        if not items:
            st.info('Isi spesifikasi dulu untuk melihat preview.')

    if st.button('Generate', type='primary', use_container_width=True):
        error = None
        if bg_file is None:
            error = 'Background wajib diupload.'
        elif not items:
            error = 'Spesifikasi wajib diisi.'
        elif not photo_files:
            error = 'Foto produk wajib diupload.'
        elif len(photo_files) != len(items):
            error = f'Jumlah foto ({len(photo_files)}) harus sama dengan jumlah spesifikasi ({len(items)}).'

        if error:
            st.error(error)
            return

        try:
            background = Image.open(bg_file).convert('RGBA')
            rendered_files = []
            preview_images = []
            progress = st.progress(0, text='Menyiapkan render...')

            for idx, (item, photo_file) in enumerate(zip(items, photo_files), start=1):
                photo = Image.open(photo_file).convert('RGBA')
                result = render_card(background, photo, item)
                filename = f"{sanitize_filename(f'{idx}-{item.title}')}.png"
                payload = image_to_bytes(result)
                rendered_files.append((filename, payload))
                preview_images.append((item, result, filename))
                progress.progress(idx / len(items), text=f'Generate {idx} / {len(items)}')

            st.success(f'Selesai. {len(rendered_files)} file berhasil dibuat.')

            if len(rendered_files) == 1:
                st.download_button(
                    'Download PNG',
                    data=rendered_files[0][1],
                    file_name=rendered_files[0][0],
                    mime='image/png',
                    use_container_width=True,
                )
            else:
                zip_bytes = build_zip(rendered_files)
                st.download_button(
                    'Download ZIP',
                    data=zip_bytes,
                    file_name='hasil-generate.zip',
                    mime='application/zip',
                    use_container_width=True,
                )

            st.subheader('Preview Hasil')
            preview_cols = st.columns(2, gap='large')
            for i, (item, image, filename) in enumerate(preview_images):
                with preview_cols[i % 2]:
                    st.image(image, caption=f'{i+1}. {item.title}', use_container_width=True)
                    st.caption(item.raw)
                    if item.selling_points:
                        st.write(' | '.join(item.selling_points))
                    st.download_button(
                        f'Download PNG #{i+1}',
                        data=rendered_files[i][1],
                        file_name=filename,
                        mime='image/png',
                        key=f'dl_{i}',
                        use_container_width=True,
                    )

        except Exception as exc:
            st.error(f'Terjadi kesalahan saat generate: {exc}')


if __name__ == '__main__':
    main()
