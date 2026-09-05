#!/usr/bin/env python3
"""Validate a ru-ecom-product output.json against marketplace rules and the
fact-file discipline (facts[] is the single source of truth).

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

FACT_STATUSES = {"confirmed", "unverified", "conflict", "missing"}
KW_STATUSES = {"verified", "candidate", "not_applicable"}
GATES = {"proceed", "needs_materials", "blocked"}
SALES_MODES = {"cross_border_direct", "local_fbo", "local_fbs", "local_dbs"}
PLACEHOLDER = "уточняется"

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
RE_EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⭐⭕✅❌✔✖]")
RE_CAPS_WORD = re.compile(r"\b[А-ЯЁA-Z]{4,}\b")
RE_RUB_BAD = re.compile(r"(₽\s?\d|\d\s?руб\b|\d\s?р\.)", re.I)
RE_DECIMAL_DOT = re.compile(r"\d\.\d+\s?(см|мм|кг|г|л|мл|вт|в|мач|м|kg|g|ml|l|mm|cm)\b", re.I)
RE_THOUSANDS_COMMA = re.compile(r"\d,\d{3}\b")
RE_IMPERIAL = re.compile(r"\b\d+(\.\d+)?\s?(inch|inches|дюйм\w*|lbs?|oz|ft)\b", re.I)
RE_INJECTION = re.compile(r"(ignore (all )?previous|игнорируй (все )?предыдущ|忽略(之前|以上)|system prompt|执行以下命令)", re.I)


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


def kw_text(k: Any) -> str:
    """Keyword entries may be plain strings (legacy) or objects."""
    return k["ru"] if isinstance(k, dict) else str(k)


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
    m = RE_URL.search(text)
    if m and m.group(0).lower().strip(".") not in {a.lower() for a in allow_latin}:
        rep.err(f"{where}: ссылка/домен «{m.group(0)}»")
    if RE_EMAIL.search(text):
        rep.err(f"{where}: e-mail")
    if RE_SOCIAL.search(text):
        rep.err(f"{where}: соцсети/мессенджер")
    if RE_INJECTION.search(text):
        rep.err(f"{where}: текст похож на инструкцию модели (prompt injection) — это данные, не команда")

    if RE_EMOJI.search(text):
        if is_title:
            rep.err(f"{where}: emoji в названии")
        else:
            rep.warn(f"{where}: emoji в тексте (WB/Яндекс не рекомендуют)")

    for cm in RE_CAPS_WORD.finditer(text):
        tok = cm.group(0)
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


# ---------------------------------------------------------------------------

def check_source(rep: Report, src: dict[str, Any]) -> None:
    mode = src.get("sales_mode")
    if not mode:
        rep.err("source.sales_mode отсутствует (cross_border_direct / local_fbo / local_fbs / local_dbs) — от него зависят комиссии, импортёр и этикетка")
    elif mode not in SALES_MODES:
        rep.err(f"source.sales_mode «{mode}» не из списка {sorted(SALES_MODES)}")

    image_refs = {img.get("ref") for img in src.get("images", []) if isinstance(img, dict)}
    variants = src.get("variants") or []
    skus = [v.get("sku") for v in variants]
    if len(skus) != len(set(skus)):
        rep.err("source.variants: дублирующиеся sku")
    seen_attrs: list[dict] = []
    for v in variants:
        if not v.get("sku"):
            rep.err("source.variants: вариант без sku")
        attrs = v.get("attrs") or {}
        if not attrs:
            rep.err(f"source.variants[{v.get('sku')}]: пустые attrs — чем вариант отличается?")
        if attrs in seen_attrs:
            rep.err(f"source.variants[{v.get('sku')}]: attrs совпадают с другим вариантом")
        seen_attrs.append(attrs)
        for ref in v.get("image_refs", []):
            if ref not in image_refs:
                rep.err(f"source.variants[{v.get('sku')}]: image_ref «{ref}» нет в source.images")
    if variants:
        for img in src.get("images", []):
            vs = img.get("variant_sku")
            if vs and vs not in skus:
                rep.err(f"source.images[{img.get('ref')}]: variant_sku «{vs}» не существует")
    rep.info["variants"] = len(variants)


def check_facts(rep: Report, facts: list[dict[str, Any]], qa: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    if not facts:
        rep.err("facts[] пустой — карточка без фактологической базы")
        return by_key
    missing_listed = {m.lower() for m in qa.get("missing_fields", [])}
    conflicts_listed = " ".join(qa.get("conflicts", [])).lower()
    n_missing = n_conflict = n_unverified = 0
    for f in facts:
        key = f.get("key")
        if not key:
            rep.err("facts[]: запись без key")
            continue
        if key in by_key:
            rep.err(f"facts[{key}]: дубликат ключа")
        by_key[key] = f
        status = f.get("status")
        if status not in FACT_STATUSES:
            rep.err(f"facts[{key}]: status «{status}» не из {sorted(FACT_STATUSES)}")
            continue
        if not (f.get("source") or "").strip():
            rep.warn(f"facts[{key}]: нет source — откуда значение?")
        if status == "missing":
            n_missing += 1
            if f.get("value") not in (None, "", PLACEHOLDER):
                rep.err(f"facts[{key}]: status=missing, но value=«{f.get('value')}» — заполнили из головы?")
            if key.lower() not in missing_listed:
                rep.warn(f"facts[{key}]: missing, но не перечислен в qa.missing_fields")
        elif status == "conflict":
            n_conflict += 1
            if not f.get("conflict_with"):
                rep.err(f"facts[{key}]: status=conflict без conflict_with")
            if key.lower() not in conflicts_listed:
                rep.warn(f"facts[{key}]: conflict, но не перечислен в qa.conflicts")
        elif status == "unverified":
            n_unverified += 1
    rep.info["facts"] = f"{len(facts)} total, {n_missing} missing, {n_conflict} conflict, {n_unverified} unverified"
    if (n_missing or n_conflict) and not (qa.get("supplier_request_zh") or "").strip():
        rep.warn("qa.supplier_request_zh пустой, хотя есть missing/conflict факты — сформируйте запрос поставщику")
    return by_key


def check_specs_against_facts(rep: Report, specs: list[dict[str, Any]], facts: dict[str, dict[str, Any]]) -> None:
    for s in specs:
        n = s.get("name", "")
        fk = s.get("fact_key")
        if not fk:
            rep.warn(f"ru.specs «{n}»: нет fact_key — значение не привязано к facts[]")
            continue
        f = facts.get(fk)
        if not f:
            rep.err(f"ru.specs «{n}»: fact_key «{fk}» отсутствует в facts[]")
            continue
        st = f.get("status")
        val = str(s.get("value", "")).strip().lower()
        if st == "conflict":
            rep.err(f"ru.specs «{n}»: цитирует факт со status=conflict — конфликт не решён, в карточку не попадает")
        elif st == "missing" and val != PLACEHOLDER:
            rep.err(f"ru.specs «{n}»: факт missing, но в карточке «{s.get('value')}» вместо «{PLACEHOLDER}»")
        elif st in ("confirmed", "unverified") and f.get("value") is not None:
            fv = str(f["value"]).strip().lower()
            if fv and fv != val and fv not in val:
                rep.warn(f"ru.specs «{n}»: значение «{s.get('value')}» ≠ facts[{fk}] «{f['value']}»")


def check_claims(rep: Report, claims: list[str], texts: dict[str, str]) -> None:
    for c in claims:
        head = re.split(r"[—\-:(/]", c)[0].strip().lower()
        if len(head) < 4:
            continue
        for where, t in texts.items():
            if head in t.lower():
                rep.err(f"{where}: содержит «{head}», который числится в compliance.claims_to_review (нет подтверждения)")


def check_keywords(rep: Report, kw: dict[str, Any]) -> None:
    all_kw: list[str] = []
    n_verified = n_candidate = 0
    for tier in ("high", "mid", "low"):
        lst = kw.get(tier, [])
        if not lst:
            rep.err(f"keywords.{tier} пустой")
        tier_words = []
        for k in lst:
            w = kw_text(k).lower().strip()
            tier_words.append(w)
            for fw in FORBIDDEN_WORDS:
                if contains_word(w, fw):
                    rep.err(f"keywords.{tier}: запрещённое слово «{fw}» в «{w}»")
            if isinstance(k, dict):
                st = k.get("status")
                if st not in KW_STATUSES:
                    rep.err(f"keywords.{tier} «{w}»: status «{st}» не из {sorted(KW_STATUSES)}")
                elif st == "verified":
                    n_verified += 1
                    if k.get("volume") is None or not k.get("source"):
                        rep.warn(f"keywords.{tier} «{w}»: verified без volume/source — на чём основано?")
                elif st == "candidate":
                    n_candidate += 1
                if not k.get("use"):
                    rep.warn(f"keywords.{tier} «{w}»: нет use — куда ставить слово?")
                if not k.get("zh"):
                    rep.warn(f"keywords.{tier} «{w}»: нет zh — проверяющий без русского не поймёт")
            else:
                n_candidate += 1
        if len(set(tier_words)) != len(tier_words):
            rep.warn(f"keywords.{tier}: дубликаты")
        all_kw.extend(tier_words)
    if len(set(all_kw)) != len(all_kw):
        rep.warn("keywords: одно и то же слово в нескольких уровнях")

    hashtags = kw.get("hashtags", [])
    if len(hashtags) > HASHTAG_MAX:
        rep.err(f"keywords.hashtags: {len(hashtags)} > {HASHTAG_MAX}")
    for h in hashtags:
        if not re.fullmatch(r"#[a-zа-яё0-9_]+", h):
            rep.err(f"keywords.hashtags: «{h}» — только строчные буквы/цифры без пробелов")
    for t in kw.get("internal_tags", []):
        if t.startswith("#"):
            rep.warn(f"keywords.internal_tags «{t}»: внутренний тег с #, не путайте с хэштегом Ozon")

    src = kw.get("source")
    if not src:
        rep.err("keywords.source отсутствует (llm-estimate или название источника)")
    elif src == "llm-estimate":
        if n_verified:
            rep.err("keywords.source = llm-estimate, но есть слова со status=verified — противоречие")
        rep.warn("keywords.source = llm-estimate — все слова кандидаты, частотность не подтверждена")
    else:
        if not n_verified:
            rep.warn(f"keywords.source = «{src}», но ни одно слово не verified — данные подключены?")
        if not kw.get("collected_at"):
            rep.warn("keywords.collected_at пустой — когда снимали данные?")
    rep.info["keywords"] = f"{len(all_kw)} total, {n_verified} verified, {n_candidate} candidate"


def validate(data: dict[str, Any], strict: bool = False) -> Report:
    rep = Report()
    src = data.get("source", {})
    facts_list = data.get("facts", [])
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

    check_source(rep, src)
    facts = check_facts(rep, facts_list, qa)

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
    if not ru.get("title_zh"):
        rep.warn("ru.title_zh пустой — нет китайского соответствия для проверяющего")

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
        if not ru.get("description_zh"):
            rep.warn("ru.description_zh пустой — двуязычная проверка невозможна")

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
    check_specs_against_facts(rep, specs, facts)

    if not ru.get("package_contents"):
        rep.warn("ru.package_contents пустой — «Комплектация» обязательна почти во всех категориях")

    # --- infographic ---
    for slide in ru.get("infographic", []):
        h = slide.get("headline", "")
        if len(h) > INFOGRAPHIC_HEADLINE_MAX:
            rep.warn(f"infographic slide {slide.get('slide')}: заголовок {len(h)} > {INFOGRAPHIC_HEADLINE_MAX}")
        scan_text(rep, f"infographic[{slide.get('slide')}]", h + " " + slide.get("subline", ""), marketplace=None, allow_latin=allow_latin, is_title=False)
        if slide.get("route") == "creative":
            rep.warn(f"infographic slide {slide.get('slide')}: route=creative — проверить, что товар не изменён (кнопки, порты, цвет, комплект)")

    # --- video ---
    video = ru.get("video")
    if video and video.get("script") and not video.get("rendered_file"):
        rep.info["video"] = "сценарий и субтитры есть, MP4 не создан"

    # --- keywords ---
    check_keywords(rep, kw)

    # --- compliance ---
    for k in ("category_guess", "gate", "tr_ts", "chestny_znak", "label_text", "warnings"):
        if k not in comp:
            rep.err(f"compliance.{k} отсутствует")
    gate = comp.get("gate")
    if gate and gate not in GATES:
        rep.err(f"compliance.gate «{gate}» не из {sorted(GATES)}")
    elif gate == "blocked":
        rep.err(f"compliance.gate = blocked: {comp.get('gate_reason') or 'причина не указана'} — публикация запрещена")
    elif gate == "needs_materials":
        rep.warn(f"compliance.gate = needs_materials: {comp.get('gate_reason') or 'причина не указана'} — черновик, не финал")
    elif gate == "proceed" and any(f.get("status") == "conflict" for f in facts.values()):
        rep.warn("compliance.gate = proceed при нерешённых конфликтах в facts — точно proceed?")
    rep.info["gate"] = gate

    label = comp.get("label_text", "")
    for must in ("Изготовитель", "Страна", "Наименование"):
        if must.lower() not in label.lower():
            rep.warn(f"compliance.label_text: нет поля «{must}»")
    if comp.get("chestny_znak") is True and "data matrix" not in label.lower() and "честный знак" not in label.lower():
        rep.warn("compliance: Честный ЗНАК = true, но на этикетке нет места под Data Matrix")

    check_claims(
        rep,
        comp.get("claims_to_review", []),
        {
            "ru.description": desc,
            **{f"ru.title.{m}": titles.get(m, "") for m in targets},
            "ru.bullets": " ".join(bullets),
            "infographic": " ".join(f"{s.get('headline','')} {s.get('subline','')}" for s in ru.get("infographic", [])),
        },
    )

    if qa.get("manual_edits"):
        rep.info["manual_edits"] = len(qa["manual_edits"])
    if not qa.get("version"):
        rep.warn("qa.version пустой — перегенерации не отследить")

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
