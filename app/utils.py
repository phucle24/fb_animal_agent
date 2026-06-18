import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo


def strip_code_fences(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def safe_json_loads(text: str) -> dict:
    cleaned = strip_code_fences(text)
    return json.loads(cleaned)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def now_str(tz_name: str) -> str:
    return datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M:%S")


def chunk_lines(text: str, max_chars: int = 20) -> list[str]:
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        if len(test) <= max_chars:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def matchup_measure_label(animal: dict) -> str:
    explicit_label = str(animal.get("measure_label") or "").strip()
    if explicit_label:
        return explicit_label

    name_text = f"{animal.get('name_vi', '')} {animal.get('name_en', '')}".lower()
    value_text = str(animal.get("height", "")).lower()

    if "sải cánh" in value_text:
        return "Sải cánh"
    if any(word in value_text for word in ("dài", "chiều dài")):
        return "Chiều dài"
    if any(word in value_text for word in ("cao vai", "vai")):
        return "Chiều cao vai"

    wingspan_keywords = (
        "chim",
        "đại bàng",
        "ưng",
        "cắt",
        "falcon",
        "eagle",
        "hawk",
        "condor",
        "owl",
        "vulture",
    )
    length_keywords = (
        "rắn",
        "trăn",
        "snake",
        "python",
        "anaconda",
        "cobra",
        "viper",
        "cá",
        "fish",
        "shark",
        "whale",
        "dolphin",
        "mực",
        "squid",
        "octopus",
        "cá sấu",
        "alligator",
        "crocodile",
        "thằn lằn",
        "kỳ đà",
        "komodo",
        "lizard",
        "eel",
    )
    shoulder_height_keywords = (
        "chó",
        "sói",
        "dingo",
        "coyote",
        "báo",
        "sư tử",
        "hổ",
        "mèo",
        "gấu",
        "linh cẩu",
        "hyena",
        "dog",
        "wolf",
        "leopard",
        "jaguar",
        "lion",
        "tiger",
        "bear",
        "cat",
    )

    if any(keyword in name_text for keyword in wingspan_keywords):
        return "Sải cánh"
    if any(keyword in name_text for keyword in length_keywords):
        return "Chiều dài"
    if any(keyword in name_text for keyword in shoulder_height_keywords):
        return "Chiều cao vai"
    return "Chiều cao"


def matchup_measure_value(animal: dict) -> str:
    value = " ".join(str(animal.get("height", "")).split()).strip()
    return re.sub(
        r"^(chiều\s+dài|chiều\s+cao\s+vai|chiều\s+cao|sải\s+cánh|dài|cao)\s*[:：-]?\s*",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
