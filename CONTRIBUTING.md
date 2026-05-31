# 参与改进 GEOVisibilityTool

> **本项目绝不自动收集任何遥测(telemetry)数据。**
> 改进完全依赖社区主动分享。下面是 3 种贡献方式,按"门槛从低到高"排列。

---

## 隐私立场

GEOVisibilityTool 不内置任何自动上传 / 调用第三方 API / 写远端日志的行为。所有数据停留在你的本地测试目录里,**只有你自己看得到原始 probe 数据**。

如果你想帮助改进工具,本文档提供了**主动**分享数据的三种途径,核心原则:

1. **永远 opt-in,永不静默**:每次分享都需要你手动触发命令、检查输出、上传文件
2. **品牌信息自动去敏**:`scripts/make-bundle.py` 把你的品牌名 / 竞品名 / URL 路径都替换成 `BRAND_X` / `COMPETITOR_OWNED_DOMAIN_N`
3. **公开透明**:所有贡献走 GitHub Issues / Pull Requests / Discussions,审计链 100% 可见

---

## 三种贡献方式

### 1. 📊 提交 Issue(最低门槛)

发现以下情况,**任选模板提交 GitHub Issue**:
[https://github.com/KnightMafiaLau/GEOVisibilityTool/issues/new/choose](https://github.com/KnightMafiaLau/GEOVisibilityTool/issues/new/choose)

| 模板 | 何时用 |
|---|---|
| 🔧 **Recipe Broken** | 某个 LLM 的 DOM scrape 失效(panel 不出来 / 抓 0 / verify-log 报 anomaly)— 用于持续修复 per-LLM citation recipe |
| 💭 **Query Feedback** | 某条生成的 query 太空泛 / 复合题 / 不像真实用户问 — 用于优化 `geo-queries` 生成规则 |
| 📊 **Channel Pattern** | 跨垂类发现某 LLM × intent × channel 的反常识/强信号(如 Qwen 在了解原理类查 Google Patents)— 用于积累 cross-vertical insight |

**强烈推荐 + 上 bundle**:

```bash
python3 scripts/make-bundle.py <你的测试目录> [--vertical 行业类别]
```

生成 `bundle-<timestamp>.json`,**手动 cat 看一眼**(确认无敏感信息后)拖到 issue 里。

bundle 包含:
- per-LLM 健康度(panel 打开率 / urls 数 / citations 数 / anomaly count)
- per-intent 引用域名 pattern(域名 + 出现次数;**品牌官网 → `BRAND_OWNED_DOMAIN`,竞品官网 → `COMPETITOR_OWNED_DOMAIN_N`**)
- 总览(query 数 / URL 观测数 / 哪些 LLM 有 anomaly)

bundle **不含**:
- 你的品牌名 / 竞品名(原始)
- query 原文(可能暴露垂类细节)
- LLM 回答内容(evidence 原句)
- 完整 URL 路径或查询参数

---

### 2. 🚀 发 Pull Request(中等门槛)

适合**直接改进代码 / SKILL.md** 的场景:

**典型 PR 类型**:

| PR 类型 | 改哪里 | 例子 |
|---|---|---|
| 🔧 修 recipe | `skills/geo-probe/SKILL.md` 的 §6.5 per-LLM recipe | "Qwen panel selector 改了 `_xxxx` → `_yyyy`,更新 JS extractor" |
| 💭 改 query 规则 | `skills/geo-queries/SKILL.md` 的硬规则 / few-shot | "新增硬规则:某些垂类(医疗/法律)需 disclaimer 措辞" |
| 📊 加 LLM 预设 | `skills/geo-probe/SKILL.md` + 新建 §6.5.X recipe | "支持 Perplexity / Gemini / Claude.ai 等海外 LLM" |
| 🎨 改 report 模板 | `skills/geo-report/SKILL.md` 的 HTML 模板 | "Hero 卡片加趋势对比(本月 vs 上月)" |
| 🐛 修 bug | 任何 | 通常先 issue 再 PR |

**PR 流程**:
1. Fork → branch → commit(commit message 清晰)
2. **测试改动**:对 SKILL.md 的改动,需附"实际跑过一次 probe / analyze / report 的截图或 bundle"证明 work
3. 提 PR,标题清晰,description 包含:**改了什么 + 为什么改 + 怎么验证**
4. Maintainer review → merge

**SKILL.md 改动的特殊要求**:
- 保留原作者署名(`KnightMafiaLau`)
- 保留水印 CSS(`GEOVisibilityTool · KnightMafiaLau`)
- 不破坏 Constitution 6 条(详见 CONSTITUTION.md)

---

### 3. 💬 Discussions(社区讨论)

不适合开 issue 但想跟社区交流的话题:

- 分享 GEO 投放实战经验(投了 N 周,LLM 端可见度变化)
- 讨论 GEO 方法论(visibility 该怎么算、零命中该怎么定义)
- 讨论与其他 GEO 工具的协作模式
- 提想法(还没成型的 feature suggestion)

[https://github.com/KnightMafiaLau/GEOVisibilityTool/discussions](https://github.com/KnightMafiaLau/GEOVisibilityTool/discussions)

---

## 哪些贡献最有价值

按对工具改进的实际影响排序(maintainer 视角):

1. **🥇 Recipe broken bundle**(影响最高)
   各 LLM 网页端不定期改版,DOM selector 失效,导致 citation 抓不全。社区贡献的 bundle + recipe broken issue 是修复速度的最大 multiplier。

2. **🥈 Channel pattern 分享**(中长期价值)
   单个用户跑 1 个垂类只能看到自己那一面;社区跨垂类汇总后能发现"哪些 LLM 在哪些场景下有反常识偏好"——这些 cross-vertical insight 进一步沉淀到 `geo-channels` 的投放形态 mapping 里。

3. **🥉 Query feedback**(渐进改进)
   `geo-queries` 的生成规则是基于经验性 few-shot 优化的,真实使用中暴露的"这条 query 没用 / 太抽象 / 不像真人问"反馈直接喂回 SKILL.md 的硬规则。

4. **代码 PR**(突破性改进)
   加新 LLM 支持 / 加新分析维度 / 加新报告类型 — 这些是工具能力上限的提升,门槛高但价值大。

---

## Code of Conduct(简版)

- 尊重所有贡献者,不论经验水平
- 反馈具体、对事不对人
- 不提交含真实品牌 / 用户数据的 issue 或 PR(bundle 自动去敏,但手动整理时也要小心)
- 不利用本项目搞批量低质量内容生产(详见 README §一 1.2 GEO 本质 — 不是 hack AI)

---

## License

贡献的所有代码 / 文档默认按 Apache License 2.0 释出(同主项目)。
你的署名将出现在 CHANGELOG.md 对应版本条目下。

详见 [LICENSE](LICENSE) + [NOTICE](NOTICE)。
