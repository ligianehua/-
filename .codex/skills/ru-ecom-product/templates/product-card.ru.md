# {{ru.title.ozon}}

**Категория:** {{compliance.category_guess}} · **Бренд:** {{source.brand}} · **Артикул:** {{source.sku}}
**Режим продаж:** {{source.sales_mode}} · **Версия:** {{qa.version}}

> **Статус проверки: {{compliance.gate}}** — {{compliance.gate_reason}}

## Названия по площадкам

| Площадка | Название | Длина | 中文对照 |
|---|---|---|---|
| Ozon | {{ru.title.ozon}} | {{len}} / 200 | {{ru.title_zh}} |
| Wildberries | {{ru.title.wildberries}} | {{len}} / 60 | |
| Яндекс Маркет | {{ru.title.yandex_market}} | {{len}} / 150 | |

## Описание · 描述

| Русский | 中文 |
|---|---|
{{#each_paragraph ru.description ru.description_zh}}
| {{ru}} | {{zh}} |
{{/each_paragraph}}

## Преимущества · 卖点（для инфографики）

| Русский | 中文 |
|---|---|
{{#each ru.bullets}}
| {{this}} | {{../ru.bullets_zh.[@index]}} |
{{/each}}

## Характеристики · 参数

| Характеристика | Значение | Источник | Статус |
|---|---|---|---|
{{#each ru.specs}}
| {{name}} | {{value}} {{unit}} | {{fact.source}} | {{fact.status}} |
{{/each}}

## Варианты · 变体

| SKU | Атрибуты | Фото |
|---|---|---|
{{#each source.variants}}
| {{sku}} | {{attrs}} | {{image_refs}} |
{{/each}}

## Комплектация

{{#each ru.package_contents}}
- {{this}}
{{/each}}

## Инфографика · 图文（слайды）

| # | Заголовок | Подзаголовок | 中文 | Фото | Маршрут |
|---|---|---|---|---|---|
{{#each ru.infographic}}
| {{slide}} | {{headline}} | {{subline}} | {{headline_zh}} | {{image_ref}} | {{route}} |
{{/each}}

## Видео

Файл: {{ru.video.rendered_file}} {{#unless ru.video.rendered_file}}（**видео не создано** — есть только сценарий и субтитры）{{/unless}}

{{#each ru.video.script}}
- `{{time}}` {{visual}} → «{{voiceover}}» · {{voiceover_zh}}
{{/each}}

## FAQ

{{#each ru.faq}}
**В:** {{q}} · {{q_zh}}
**О:** {{a}} · {{a_zh}}
{{/each}}

## Ключевые слова · 关键词

Источник: **{{keywords.source}}** · Дата: {{keywords.collected_at}}

| Уровень | Слово | 中文 | Куда | SKU | Статус |
|---|---|---|---|---|---|
{{#each keywords.high}}| ВЧ | {{ru}} | {{zh}} | {{use}} | {{sku}} | {{status}} |
{{/each}}{{#each keywords.mid}}| СЧ | {{ru}} | {{zh}} | {{use}} | {{sku}} | {{status}} |
{{/each}}{{#each keywords.low}}| НЧ | {{ru}} | {{zh}} | {{use}} | {{sku}} | {{status}} |
{{/each}}

- **Минус-слова:** {{keywords.negative}}
- **Хэштеги (только Ozon):** {{keywords.hashtags}}
- **Внутренние теги (кабинет продавца):** {{keywords.internal_tags}}

## Соответствие · 合规

- **ТР ТС / ЕАЭС:** {{compliance.tr_ts}}
- **Честный ЗНАК:** {{compliance.chestny_znak}}
- **Заявления без подтверждения (не в карточке):** {{compliance.claims_to_review}}
- **Предупреждения:** {{compliance.warnings}}

### Этикетка

```
{{compliance.label_text}}
```

## Конфликты и пробелы · 冲突与缺失

**Конфликты (не решены, в карточку не попали):**
{{#each qa.conflicts}}
- {{this}}
{{/each}}

**Уточнить:**
{{#each qa.missing_fields}}
- {{this}}
{{/each}}

**Ручные правки (не перезаписывать при перегенерации):**
{{#each qa.manual_edits}}
- {{this}}
{{/each}}

## 给供应商的补资料信息

```
{{qa.supplier_request_zh}}
```
