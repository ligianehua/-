# 俄罗斯跨境电商 · 商品卡片 Skill（Codex / Claude Code）

把中文产品资料变成 **Ozon / Wildberries / Яндекс Маркет** 可直接上架的俄语商品卡片：
标题、描述、参数表、图文（инфографика）文案、视频脚本、分层关键词、标签，外加合规检查和字数校验。

```
输入：产品名称 + 图片 + 视频 + 参数 + 介绍
  ↓  Step 0  归一化（单位、尺码、品牌保留拉丁）
  ↓  Step 1  看图看视频，提取可见卖点
  ↓  Step 2  俄语卡片（三平台标题 / 描述 / 参数 / 属性映射 / 图文 / FAQ）
  ↓  Step 3  关键词 ВЧ / СЧ / НЧ + 反向词 + #标签
  ↓  Step 4  合规：ТР ТС / ЕАС、Честный ЗНАК、俄语标签、广告法红线
  ↓  Step 5  scripts/validate_card.py 校验
输出：output.json（templates/output.schema.json）+ Markdown 卡片
```

## 安装

### Codex CLI

仓库级（推荐，随项目走）：本仓库已经放在 `.codex/skills/ru-ecom-product/`，在仓库根目录启动 Codex 即可被发现。

用户级（所有项目可用）：

```bash
mkdir -p ~/.codex/skills
cp -r .codex/skills/ru-ecom-product ~/.codex/skills/
```

### Claude Code

`.claude/skills/ru-ecom-product` 是指向同一目录的软链接，在仓库里直接 `/ru-ecom-product` 或自然语言触发。

## 用法

```
用 ru-ecom-product 处理这个产品：
名称：磁吸无线充电宝 10000mAh，品牌 Nexora，型号 MagGo 10
参数：…
介绍：…
图片：img_01.jpg … 
目标平台：Ozon、Wildberries
```

完整示例见 `.codex/skills/ru-ecom-product/examples/`。

校验：

```bash
python3 .codex/skills/ru-ecom-product/scripts/validate_card.py output.json
python3 .codex/skills/ru-ecom-product/scripts/validate_card.py output.json --strict --json
```

## 目录

```
.codex/skills/ru-ecom-product/
├── SKILL.md                 # 工作流主文件（Codex 读这个）
├── agents/openai.yaml       # Codex 界面元数据
├── references/
│   ├── marketplaces.md      # Ozon / WB / Яндекс 字数、字段、图片规格、禁用词
│   ├── russian-style.md     # 俄语文案风格、单位、尺码表
│   ├── keywords.md          # ВЧ/СЧ/НЧ 关键词方法与数据源
│   ├── compliance.md        # ЕАС、ТР ТС、Честный ЗНАК、标签、广告法
│   └── glossary.md          # 中→俄 电商术语表
├── templates/
│   ├── intake.md            # 缺资料时的追问模板
│   ├── output.schema.json   # 输出 JSON Schema
│   └── product-card.ru.md   # Markdown 渲染模板
├── scripts/validate_card.py # 校验脚本（标准库）
└── examples/                # 输入 / 输出样例
docs/ROADMAP.md              # 后续功能与 MCP 设计
AGENTS.md                    # Codex 仓库级约定
```

## 现在的边界（别自欺）

- **关键词没有搜索量数据。** 没接 Wordstat / WB / Ozon 后台之前，关键词是语言学估计，`keywords.source` 会标 `llm-estimate`。
- **合规是清单，不是法律意见。** 证书类型和 Честный ЗНАК 范围要认证机构确认。
- **平台字数限制会变。** 常量在 `references/marketplaces.md` 与 `scripts/validate_card.py` 两处，改一处记得改另一处。

后续要做什么、怎么做成 MCP，见 [docs/ROADMAP.md](docs/ROADMAP.md)。
