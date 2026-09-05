# {{ru.title.ozon}}

**Категория:** {{compliance.category_guess}}
**Бренд:** {{source.brand}} · **Артикул:** {{source.sku}}

## Названия по площадкам

| Площадка | Название | Длина |
|---|---|---|
| Ozon | {{ru.title.ozon}} | {{len}} / 200 |
| Wildberries | {{ru.title.wildberries}} | {{len}} / 60 |
| Яндекс Маркет | {{ru.title.yandex_market}} | {{len}} / 150 |

## Описание

{{ru.description}}

## Преимущества (для инфографики)

{{#each ru.bullets}}
- {{this}}
{{/each}}

## Характеристики

| Характеристика | Значение |
|---|---|
{{#each ru.specs}}
| {{name}} | {{value}} {{unit}} |
{{/each}}

## Комплектация

{{#each ru.package_contents}}
- {{this}}
{{/each}}

## Инфографика (слайды)

{{#each ru.infographic}}
**Слайд {{slide}}** ({{image_ref}}): **{{headline}}** — {{subline}}
{{/each}}

## Видео

{{#each ru.video.script}}
- `{{time}}` {{visual}} → «{{voiceover}}»
{{/each}}

## FAQ

{{#each ru.faq}}
**В:** {{q}}
**О:** {{a}}
{{/each}}

## Ключевые слова

- **ВЧ:** {{keywords.high}}
- **СЧ:** {{keywords.mid}}
- **НЧ:** {{keywords.low}}
- **Минус-слова:** {{keywords.negative}}
- **Хэштеги (Ozon):** {{keywords.hashtags}}
- **Источник:** {{keywords.source}}

## Соответствие

- **ТР ТС / ЕАЭС:** {{compliance.tr_ts}}
- **Честный ЗНАК:** {{compliance.chestny_znak}}
- **Предупреждения:** {{compliance.warnings}}

### Этикетка

```
{{compliance.label_text}}
```

## Что нужно уточнить

{{#each qa.missing_fields}}
- {{this}}
{{/each}}
