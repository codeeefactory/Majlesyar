from __future__ import annotations

PRODUCT_LABELS: tuple[str, ...] = (
    "halva",
    "date",
    "orange",
    "tangerine",
    "banana",
    "cake",
    "juice",
)

PERSIAN_LABELS: dict[str, str] = {
    "halva": "حلوا",
    "date": "خرما",
    "orange": "پرتقال",
    "tangerine": "نارنگی",
    "banana": "موز",
    "cake": "کیک",
    "juice": "آبمیوه",
}

PERSIAN_TO_ENGLISH: dict[str, str] = {value: key for key, value in PERSIAN_LABELS.items()}

DEFAULT_MODEL_INPUT_SIZE = 224
