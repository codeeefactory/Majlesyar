from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import fitz


PDF_PATH = next(
    path
    for path in (Path.home() / "Downloads" / "Telegram Desktop").glob("*.pdf")
    if "260607_025646" in path.name
)
OUTPUT_PATH = Path("Majlesyar/src/data/pdfPageContent.ts")


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value)
    text = text.replace("\r", "\n").replace("\u200c", "‌")
    text = text.replace("memorial-\nwreaths", "memorial-wreaths")
    text = text.replace("Majlesyar.com/flower/\ncongratulation-wreaths", "Majlesyar.com/flower/congratulation-wreaths")
    text = re.sub(r">\s*\n\s*p\s*\n\s*<", ">p<", text)
    for source, target in {
        "۰۸": "۸۰",
        "۰۰۱": "۱۰۰",
        "۰۰۲": "۲۰۰",
        "۴۲": "۲۴",
        "۲۱": "۱۲",
        "۰۱": "۱۰",
    }.items():
        text = text.replace(source, target)
    text = re.sub(r" ([،؛؟:,.])([\u0600-\u06FF]+)", r" \2\1", text)
    text = re.sub(r"([۰-۹])\s+٪", r"\1٪", text)
    return re.sub(r"Impossible to decode[^\n]*\n?", "", text)


def clean_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    line = re.sub(r">\s*p\s*<", " >p<", line)
    return line.strip()


def strip_tags(line: str) -> tuple[str | None, str]:
    tag = None
    text = line.strip()
    if re.search(r"(^|\s)H2\s+", text) or re.search(r"h2\s*$", text, re.I):
        tag = "h2"
        text = re.sub(r"^H2\s*", "", text, flags=re.I)
        text = re.sub(r"\s*h2\s*$", "", text, flags=re.I)
    if re.search(r"h3\s*$", text, re.I):
        tag = "h3"
        text = re.sub(r"\s*h3\s*$", "", text, flags=re.I)
    if ">p<" in text:
        tag = tag or "p"
        text = text.replace(">p<", "")
    if tag in {"h2", "h3"}:
        text = text.strip(" .")
    return tag, text.strip()


EMOJI_START = re.compile(r"^[\U0001F300-\U0001FAFF\u2300-\u27BF]")
EMOJI_ONLY = re.compile(r"^[\U0001F300-\U0001FAFF\u2300-\u27BF]+(?:️)?$")
STARTS = (
    "سوال",
    "پاسخ",
    "معرفی",
    "توضیحات",
    "نکات",
    "مزایای",
    "سوالات متداول",
    "پرداخت در محل",
    "ساختار جامع",
)
ORPHAN_LABELS = {
    "ترحیم(",
    "گل مجلس(",
    ")دسته گل(",
    "wreaths ) تاج گل ترحیم(",
    "گل(",
    "غذایی مجلس(",
}


def is_new_block(text: str, tag: str | None) -> bool:
    return tag in {"h2", "h3"} or text.startswith(STARTS) or bool(EMOJI_START.match(text))


def make_block(text: str, tag: str | None = None) -> dict[str, str]:
    block = {"text": text}
    if tag:
        block["tag"] = tag
    return block


def cleanup_block_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([،؛؟:,.])([\u0600-\u06FF]+)", r" \2\1", text)
    text = re.sub(r"(^|\s):سوال", r"\1سوال:", text)
    text = re.sub(r"(^|\s):پاسخ", r"\1پاسخ:", text)
    text = text.replace("...و", "و...")
    text = re.sub(r"([۰-۹])\s+٪", r"\1٪", text)
    return text


def blocks_from(section: str, *, prelude: str = "") -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    lines = [*prelude.splitlines(), *section.splitlines()] if prelude else section.splitlines()

    for raw_line in lines:
        line = clean_line(raw_line)
        if not line:
            continue
        if "Majlesyar.com" in line or line.startswith("📁"):
            continue
        if line in ORPHAN_LABELS:
            continue

        tag, content = strip_tags(line)
        if not content and tag in {"h2", "h3", "p"} and current:
            current["tag"] = tag
            blocks.append(current)
            current = None
            continue
        if not content:
            continue
        if current and content == current["text"]:
            continue
        if current and content in current["text"][-len(content) - 2 :]:
            continue

        if tag in {"h2", "h3"}:
            if tag == "h3" and current and current["text"].startswith("سوال"):
                content = f"{current['text']} {content}".strip()
                current = None
            if current:
                blocks.append(current)
                current = None
            blocks.append(make_block(content, tag))
            continue

        if current is not None and EMOJI_ONLY.fullmatch(current["text"]):
            current["text"] = f"{current['text']} {content}".strip()
            if tag and not current.get("tag"):
                current["tag"] = tag
        elif current is None or is_new_block(content, tag):
            if current:
                blocks.append(current)
            current = make_block(content, tag)
        else:
            current["text"] = f"{current['text']} {content}".strip()
            if tag and not current.get("tag"):
                current["tag"] = tag

        if tag == "p" and line.endswith(">p<"):
            blocks.append(current)
            current = None

    if current:
        blocks.append(current)

    deduped: list[dict[str, str]] = []
    for block in blocks:
        block["text"] = cleanup_block_text(block["text"])
        if not block["text"]:
            continue
        if deduped and deduped[-1]["text"] == block["text"]:
            continue
        deduped.append(block)
    return deduped


def main() -> None:
    fitz.TOOLS.mupdf_display_errors(False)
    with fitz.open(PDF_PATH) as doc:
        text = normalize_text("\n".join(page.get_text("text") for page in doc))

    markers = [
        ("pack", "Majlesyar.com/pack\n"),
        ("memorial", "Majlesyar.com/pack/memorial"),
        ("flower", "Majlesyar.com/flower\n"),
        ("memorialWreaths", "Majlesyar.com/flower/memorial-wreaths"),
        ("bouquets", "Majlesyar.com/flower/bouquets"),
        ("congratulatoryWreaths", "Majlesyar.com/flower/congratulation-wreaths"),
        ("flowerBox", "Majlesyar.com/flower/box"),
        ("halvaKhorma", "Majlesyar.com/halva-khorma"),
        ("food", "Majlesyar.com/food\n) منوی جامع \nتشریفات"),
        ("fingerFood", "Majlesyar.com/food/finger_food"),
        ("shalehZard", "Majlesyar.com/food/shaleh-zard"),
    ]
    positions = []
    for key, marker in markers:
        index = text.find(marker)
        if index < 0:
            raise RuntimeError(f"Marker missing: {key} {marker}")
        positions.append((key, index, marker))
    positions.sort(key=lambda item: item[1])

    prelude = text[: positions[0][1]].strip()
    sections = {}
    for index, (key, start, _marker) in enumerate(positions):
        end = positions[index + 1][1] if index + 1 < len(positions) else len(text)
        sections[key] = text[start:end]

    content = {
        key: blocks_from(section, prelude=prelude if key == "flower" else "")
        for key, section in sections.items()
    }
    if "پرداخت در محل" in prelude:
        content["pack"].insert(0, {"text": "پرداخت در محل"})

    ordered_keys = [
        "pack",
        "memorial",
        "flower",
        "memorialWreaths",
        "bouquets",
        "congratulatoryWreaths",
        "flowerBox",
        "halvaKhorma",
        "food",
        "fingerFood",
        "shalehZard",
    ]
    output_lines = [
        'import type { EventContentBlock } from "@/types/domain";',
        "",
        "export const pdfPageContentBlocks: Record<string, EventContentBlock[]> = {",
    ]
    for key in ordered_keys:
        output_lines.append(f"  {key}: [")
        for block in content[key]:
            output_lines.append(f"    {json.dumps(block, ensure_ascii=False)},")
        output_lines.append("  ],")
    output_lines.append("};")
    OUTPUT_PATH.write_text("\n".join(output_lines) + "\n", encoding="utf-8")

    for key in ordered_keys:
        chars = sum(len(block["text"]) for block in content[key])
        print(key, len(content[key]), chars)


if __name__ == "__main__":
    main()
