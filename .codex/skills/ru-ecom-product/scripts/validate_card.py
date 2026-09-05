#!/usr/bin/env python3
"""Validate a ru-ecom-product output.json against marketplace rules.

Usage:
    python3 validate_card.py output.json [--strict] [--json]

Exit code 0 = no errors (warnings allowed), 1 = errors found, 2 = bad input.
Standard library only. Limits mirror references/marketplaces.md.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Any

# --- limits (keep in sync with references/marketplaces.md) -----------------
TITLE_LIMITS = {"ozon": 200, "wildberries": 60, "yandex_market": 150, "aliexpress": 128}
DESC_LIMITS = {"ozon": 6000, "wildberries": 2000, "yandex_market": 6000, "aliexpress": 5000}
BULLET_MAX = 80
HASHTAG_MAX = 10
INFOGRAPHIC_HEADLINE_MAX = 40
MIN_CYRILLIC_SHARE = 0.55  # share of letters that must be Cyrillic in title/description

FORBIDDEN_WORDS = [
    "скидка", "скидки", "акция", "акции", "распродажа", "хит продаж", "хит",
    "лучший", "лучшая", "лучшее", "лучшие", "самый", "самая", "самое", "самые",
    "№1", "no.1", "бесплатно", "дёшево", "дешево", "оригинал 100%", "100% оригинал", "топ",
]
MEDICAL_CLAIMS = ["лечит", "излечивает", "лечебный", "лечебная", "от рака", "укрепляет иммунитет", "от боли"]
OTHER_MARKETPLACES = {
    "ozon": ["wildberries", "вайлдберриз", "яндекс маркет", "aliexpress", "алиэкспресс", "amazon", "taobao", "1688"],
    "wildberries": ["ozon", "озон", "яндекс маркет", "aliexpress", "алиэкспресс", "amazon", "taobao", "1688"],
    "yandex_market": ["ozon", "озон", "wildberries", "вайлдберриз", "aliexpress", "алиэкспресс", "amazon", "taobao", "1688"],
    "aliexpress": ["ozon", "озон", "wildberries", "вайлдберриз", "яндекс маркет", "amazon", "taobao", "1688"],
}

RE_PHONE = re.compile(r"(?<!\d)(\+?\d[\d\s\-()]{8,}\d)(?!\d)")
RE_URL = re.compile(r"(https?://|www\.|\b[\w-]+\.(ru|com|net|org|рф|shop|store)\b)", re.I)
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
RE_SOCIAL = re.compile(r"(?<![\w])@[a-z0-9_]{3,}|\b(telegram|телеграм|whatsapp|ватсап|вконтакте|vk\.com|instagram|инстаграм)\b", re.I)
RE_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⭐⭕✅❌✔✖]"
)
RE_CAPS_WORD = re.compile(r"\b[А-ЯЁA-Z]{4,}\b")
RE_RUB_BAD = re.compile(r"(₽\s?\d|\d\s?руб\b|\d\s?р\.)", re.I)
RE_DECIMAL_DOT = re.compile(r"\d\.\d+\s?(см|мм|кг|г|л|мл|вт|в|мач|м)\b", re.I)
RE_THOUSANDS_COMMA = re.compile(r"\d,\d{3}\b")
RE_IMPERIAL = re.compile(r"\b\d+(\.\d+)?\s?(inch|inches|дюйм\w*|lbs?|oz|ft)\b", re.I)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def cyrillic_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 1.0
    cyr = sum(1 for c in letters if "CYRILLIC" in unicodedata.name(c, ""))
    return cyr / len(letters)


def contains_word(text: str, word: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", text, re.I) is not None


def scan_text(rep: Report, where: str, text: str, *, marketplace: str | None, allow_latin: set[str], is_title: bool) -> None:
    lowered = text.lower()

    for w in FORBIDDEN_WORDS:
        if contains_word(lowered, w):
            rep.err(f"{where}: запрещённое слово «{w}»")
    for w in MEDICAL_CLAIMS:
        if contains_word(lowered, w):
            rep.err(f"{where}: медицинское утверждение «{w}»")
    if marketplace:
        for w in OTHER_MARKETPLACES.get(marketplace, []):
            if contains_word(lowered, w):
                rep.err(f"{where}: упоминание другой площадки «{w}»")

    if RE_PHONE.search(text):
        rep.err(f"{where}: похоже на номер телефона")
    if RE_URL.search(text):
        m = RE_URL.search(text)
        # tolerate brand-like tokens explicitly allowed
        if m and m.group(0).lower().strip(".") not in {a.lower() for a in allow_latin}:
            rep.err(f"{where}: ссылка/домен «{m.group(0)}»")
    if RE_EMAIL.search(text):
        rep.err(f"{where}: e-mail")
    if RE_SOCIAL.search(text):
        rep.err(f"{where}: соцсети/мессенджер")

    if RE_EMOJI.search(text):
        if is_title:
            rep.err(f"{where}: emoji в названии")
        else:
            rep.warn(f"{where}: emoji в тексте (WB/Яндекс не рекомендуют)")

    for m in RE_CAPS_WORD.finditer(text):
        tok = m.group(0)
        if tok not in allow_latin and tok.upper() not in {a.upper() for a in allow_latin}:
            rep.warn(f"{where}: слово капсом «{tok}» (если не бренд — переписать)")

    share = cyrillic_share(text)
    if share < MIN_CYRILLIC_SHARE:
        rep.warn(f"{where}: доля кириллицы {share:.0%} < {MIN_CYRILLIC_SHARE:.0%} — текст похож на непереведённый")

    if RE_RUB_BAD.search(text):
        rep.warn(f"{where}: формат цены — пишите «1 990 ₽»")
    if RE_DECIMAL_DOT.search(text):
        rep.warn(f"{where}: десятичная точка вместо запятой (1.5 кг → 1,5 кг)")
    if RE_THOUSANDS_COMMA.search(text):
        rep.warn(f"{where}: тысячи через запятую (20,000 → 20 000)")
    if RE_IMPERIAL.search(text):
        rep.warn(f"{where}: имперские единицы — переведите в метрические")

    if is_title:
        words = re.findall(r"[а-яёa-z0-9-]+", lowered)
        stems = [w[:5] for w in words if len(w) >= 5]
        dupes = {s for s in stems if stems.count(s) > 1}
        if dupes:
            rep.warn(f"{where}: повтор корней в названии ({', '.join(sorted(dupes))}) — риск переспама")


def validate(data: dict[str, Any], strict: bool = False) -> Report:
    rep = Report()
    src = data.get("source", {})
    ru = data.get("ru", {})
    kw = data.get("keywords", {})
    comp = data.get("compliance", {})
    qa = data.get("qa", {})

    allow_latin: set[str] = set()
    for k in ("brand", "model", "sku"):
        v = src.get(k)
        if isinstance(v, str) and v.strip():
            allow_latin.update(v.split())
    allow_latin.update({"USB", "USB-C", "PD", "QC", "TWS", "LED", "OLED", "IPS", "HDMI", "RGB", "GPS", "NFC", "SPF", "IP67", "IP68", "EAN", "RU", "EU", "ЕАС", "ТР", "ТС", "ЕАЭС", "ГОСТ", "ЗНАК"})

    targets = src.get("target_marketplaces") or list(TITLE_LIMITS.keys())

    # --- titles ---
    titles = ru.get("title", {})
    if not titles:
        rep.err("ru.title отсутствует")
    for mp in targets:
        t = titles.get(mp)
        if not t:
            rep.err(f"ru.title.{mp} отсутствует (площадка в target_marketplaces)")
            continue
        limit = TITLE_LIMITS[mp]
        rep.info[f"title_len.{mp}"] = len(t)
        if len(t) > limit:
            rep.err(f"ru.title.{mp}: {len(t)} символов > {limit}")
        elif len(t) > limit * 0.95:
            rep.warn(f"ru.title.{mp}: {len(t)}/{limit} — на грани")
        scan_text(rep, f"ru.title.{mp}", t, marketplace=mp, allow_latin=allow_latin, is_title=True)
        first = t.split()[0] if t.split() else ""
        if src.get("brand") and first.lower() == str(src["brand"]).lower():
            rep.warn(f"ru.title.{mp}: начинается с бренда — первым должен идти тип товара")

    # --- description ---
    desc = ru.get("description", "")
    if not desc:
        rep.err("ru.description отсутствует")
    else:
        rep.info["description_len"] = len(desc)
        for mp in targets:
            limit = DESC_LIMITS[mp]
            text = desc
            if mp == "wildberries" and ru.get("description_wb"):
                text = ru["description_wb"]
                rep.info["description_wb_len"] = len(text)
            if len(text) > limit:
                rep.err(f"описание для {mp}: {len(text)} > {limit}")
        scan_text(rep, "ru.description", desc, marketplace=None, allow_latin=allow_latin, is_title=False)
        for mp in targets:
            for w in OTHER_MARKETPLACES.get(mp, []):
                if contains_word(desc.lower(), w):
                    rep.err(f"ru.description: упоминание площадки «{w}» (нельзя для {mp})")
        for section in ("Характеристики", "Комплектация"):
            if section.lower() not in desc.lower():
                rep.warn(f"ru.description: нет раздела «{section}»")
        if ru.get("description_wb"):
            scan_text(rep, "ru.description_wb", ru["description_wb"], marketplace="wildberries", allow_latin=allow_latin, is_title=False)

    # --- bullets ---
    bullets = ru.get("bullets", [])
    if len(bullets) < 3:
        rep.err(f"ru.bullets: {len(bullets)} < 3")
    for i, b in enumerate(bullets, 1):
        if len(b) > BULLET_MAX:
            rep.err(f"ru.bullets[{i}]: {len(b)} > {BULLET_MAX}")
        scan_text(rep, f"ru.bullets[{i}]", b, marketplace=None, allow_latin=allow_latin, is_title=False)

    # --- specs ---
    specs = ru.get("specs", [])
    if not specs:
        rep.err("ru.specs пустой")
    seen = set()
    for s in specs:
        n = s.get("name", "")
        if n.lower() in seen:
            rep.warn(f"ru.specs: дубликат «{n}»")
        seen.add(n.lower())
        if not s.get("value"):
            rep.err(f"ru.specs «{n}»: пустое значение")
        elif str(s["value"]).strip().lower() == "уточняется" and n not in qa.get("missing_fields", []):
            rep.warn(f"ru.specs «{n}» = уточняется, но нет в qa.missing_fields")

    if not ru.get("package_contents"):
        rep.warn("ru.package_contents пустой — «Комплектация» обязательна почти во всех категориях")

    # --- infographic ---
    for slide in ru.get("infographic", []):
        h = slide.get("headline", "")
        if len(h) > INFOGRAPHIC_HEADLINE_MAX:
            rep.warn(f"infographic slide {slide.get('slide')}: заголовок {len(h)} > {INFOGRAPHIC_HEADLINE_MAX}")
        scan_text(rep, f"infographic[{slide.get('slide')}]", h + " " + slide.get("subline", ""), marketplace=None, allow_latin=allow_latin, is_title=False)

    # --- keywords ---
    for tier in ("high", "mid", "low"):
        lst = kw.get(tier, [])
        if not lst:
            rep.err(f"keywords.{tier} пустой")
        lowered = [x.lower().strip() for x in lst]
        if len(set(lowered)) != len(lowered):
            rep.warn(f"keywords.{tier}: дубликаты")
        for w in lowered:
            for f in FORBIDDEN_WORDS:
                if contains_word(w, f):
                    rep.err(f"keywords.{tier}: запрещённое слово «{f}» в «{w}»")
    all_kw = [x.lower().strip() for t in ("high", "mid", "low") for x in kw.get(t, [])]
    if len(set(all_kw)) != len(all_kw):
        rep.warn("keywords: одно и то же слово в нескольких уровнях")
    hashtags = kw.get("hashtags", [])
    if len(hashtags) > HASHTAG_MAX:
        rep.err(f"keywords.hashtags: {len(hashtags)} > {HASHTAG_MAX}")
    for h in hashtags:
        if not re.fullmatch(r"#[a-zа-яё0-9_]+", h):
            rep.err(f"keywords.hashtags: «{h}» — только строчные буквы/цифры без пробелов")
    src_kw = kw.get("source")
    if not src_kw:
        rep.err("keywords.source отсутствует (llm-estimate или название источника)")
    elif src_kw == "llm-estimate":
        rep.warn("keywords.source = llm-estimate — частотность не подтверждена данными")
    rep.info["keywords_total"] = len(all_kw)

    # --- compliance ---
    for k in ("category_guess", "tr_ts", "chestny_znak", "label_text", "warnings"):
        if k not in comp:
            rep.err(f"compliance.{k} отсутствует")
    label = comp.get("label_text", "")
    for must in ("Изготовитель", "Страна", "Наименование"):
        if must.lower() not in label.lower():
            rep.warn(f"compliance.label_text: нет поля «{must}»")
    if comp.get("chestny_znak") is True:
        if "data matrix" not in label.lower() and "честный знак" not in label.lower():
            rep.warn("compliance: Честный ЗНАК = true, но на этикетке нет места под Data Matrix")

    if strict:
        rep.errors.extend(rep.warnings)
        rep.warnings = []
    return rep


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = argv[1]
    strict = "--strict" in argv
    as_json = "--json" in argv
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Cannot read {path}: {e}", file=sys.stderr)
        return 2

    rep = validate(data, strict=strict)

    if as_json:
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings, "info": rep.info}, ensure_ascii=False, indent=2))
    else:
        for e in rep.errors:
            print(f"ERROR  {e}")
        for w in rep.warnings:
            print(f"WARN   {w}")
        for k, v in rep.info.items():
            print(f"INFO   {k} = {v}")
        print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
