# AGENTS.md

本仓库是俄罗斯跨境电商商品卡片的 Agent Skill 集合。

## 技能

- `ru-ecom-product`（`.codex/skills/ru-ecom-product/SKILL.md`）：中文产品资料 → 俄语商品卡片 + 关键词 + 合规。
  当用户提到俄语商品、Ozon、Wildberries、WB、Яндекс Маркет、俄语上架、俄语关键词时，读该 SKILL.md 并按其工作流执行。

## 约定

- 卡片内容一律俄语；对用户的说明用用户的语言。
- 输出必须符合 `.codex/skills/ru-ecom-product/templates/output.schema.json`，并通过 `scripts/validate_card.py`（0 errors）后才算完成。
- 不编造参数。缺的写 `уточняется` 并列入 `qa.missing_fields`。
- 关键词若无真实搜索数据，`keywords.source` 必须是 `llm-estimate`。
- 修改平台字数限制时，同时更新 `references/marketplaces.md` 与 `scripts/validate_card.py` 中的常量。
- 脚本只用 Python 标准库，不引入依赖。

## 测试

```bash
python3 .codex/skills/ru-ecom-product/scripts/validate_card.py .codex/skills/ru-ecom-product/examples/output.example.json
```

期望：0 error(s)。
