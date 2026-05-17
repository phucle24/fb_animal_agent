from PIL import Image, ImageDraw, ImageFont

from app.config import FONT_BOLD, FONT_REGULAR


TARGET_SIZE = (1080, 1350)


def load_font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def fit_cover(img: Image.Image, size=(1080, 1350)) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = img.size

    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)

    img = img.resize((new_w, new_h))
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def wrap_text_by_width(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        if text_width(draw, test, font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def draw_text(draw, xy, text, font, fill):
    draw.text(xy, text, font=font, fill=fill)


def overlay_single_card(
    raw_path: str,
    final_path: str,
    overlay_title: str,
    overlay_stat: str,
    overlay_hook: str,
):
    img = Image.open(raw_path).convert("RGBA")
    img = fit_cover(img, TARGET_SIZE)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    title_font = load_font(FONT_BOLD, 72)
    stat_font = load_font(FONT_BOLD, 52)
    hook_font = load_font(FONT_REGULAR, 36)
    small_font = load_font(FONT_REGULAR, 24)

    panel = (50, 60, 760, 420)
    draw.rounded_rectangle(panel, radius=28, fill=(0, 0, 0, 150))

    title = overlay_title.upper()
    title_lines = wrap_text_by_width(draw, title, title_font, 620)

    y = 95
    for line in title_lines[:3]:
        draw_text(draw, (85, y), line, title_font, (255, 255, 255, 255))
        y += 82

    badge_x1, badge_y1 = 85, y + 10
    badge_x2, badge_y2 = 500, y + 92
    draw.rounded_rectangle(
        (badge_x1, badge_y1, badge_x2, badge_y2),
        radius=20,
        fill=(255, 196, 30, 255),
    )
    draw_text(draw, (110, y + 28), overlay_stat.upper(), stat_font, (20, 20, 20, 255))

    hook_y = badge_y2 + 24
    hook_lines = wrap_text_by_width(draw, overlay_hook, hook_font, 620)
    for line in hook_lines[:2]:
        draw_text(draw, (85, hook_y), line, hook_font, (245, 245, 245, 255))
        hook_y += 42

    draw_text(draw, (60, 1290), "Ảnh minh họa AI", small_font, (255, 255, 255, 220))

    out = Image.alpha_composite(img, overlay).convert("RGB")
    out.save(final_path, quality=95)
    return final_path


def overlay_comparison_top5(
    raw_path: str,
    final_path: str,
    overlay_title: str,
    overlay_subtitle: str,
    items: list,
):
    img = Image.open(raw_path).convert("RGBA")
    img = fit_cover(img, TARGET_SIZE)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    title_font = load_font(FONT_BOLD, 68)
    subtitle_font = load_font(FONT_REGULAR, 34)
    row_name_font = load_font(FONT_BOLD, 34)
    row_stat_font = load_font(FONT_BOLD, 30)
    rank_font = load_font(FONT_BOLD, 34)
    small_font = load_font(FONT_REGULAR, 22)

    draw.rounded_rectangle((40, 40, 1040, 260), radius=28, fill=(0, 0, 0, 150))
    draw_text(draw, (70, 70), overlay_title.upper(), title_font, (255, 255, 255, 255))

    subtitle_lines = wrap_text_by_width(draw, overlay_subtitle, subtitle_font, 900)
    sub_y = 155
    for line in subtitle_lines[:2]:
        draw_text(draw, (72, sub_y), line, subtitle_font, (240, 240, 240, 255))
        sub_y += 40

    panel_y1 = 310
    panel_y2 = 1240
    draw.rounded_rectangle((40, panel_y1, 1040, panel_y2), radius=28, fill=(0, 0, 0, 165))

    start_y = 360
    row_h = 165

    for i, item in enumerate(items[:5]):
        row_top = start_y + i * row_h
        row_bottom = row_top + 125

        draw.rounded_rectangle(
            (70, row_top, 1010, row_bottom),
            radius=20,
            fill=(255, 255, 255, 24),
        )

        circle_x1, circle_y1 = 95, row_top + 20
        circle_x2, circle_y2 = 165, row_top + 90
        draw.ellipse((circle_x1, circle_y1, circle_x2, circle_y2), fill=(255, 196, 30, 255))

        rank_text = str(item["rank"])
        draw_text(draw, (120, row_top + 36), rank_text, rank_font, (0, 0, 0, 255))

        name_x = 195
        name_y = row_top + 20
        name_lines = wrap_text_by_width(draw, item["name_vi"], row_name_font, 520)

        for j, line in enumerate(name_lines[:2]):
            draw_text(draw, (name_x, name_y + j * 38), line, row_name_font, (255, 255, 255, 255))

        badge_text = item["stat"].upper()
        badge_w = text_width(draw, badge_text, row_stat_font) + 40
        badge_h = 52
        badge_x2 = 975
        badge_x1 = badge_x2 - badge_w
        badge_y1 = row_top + 32
        badge_y2 = badge_y1 + badge_h

        draw.rounded_rectangle(
            (badge_x1, badge_y1, badge_x2, badge_y2),
            radius=18,
            fill=(255, 196, 30, 255),
        )
        draw_text(draw, (badge_x1 + 20, badge_y1 + 10), badge_text, row_stat_font, (0, 0, 0, 255))

    draw_text(draw, (60, 1295), "Ảnh minh họa AI", small_font, (255, 255, 255, 220))

    out = Image.alpha_composite(img, overlay).convert("RGB")
    out.save(final_path, quality=95)
    return final_path

