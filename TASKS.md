# Tasks

最终目标：把所有模块装成一个 GEO 测试 harness。

## 跨模块状态文件

**`probe-plan.yaml`** — 整个 test run 的账本，贯穿 probe → analyze（→ report → harness）。位置：与 queries.yaml 同目录。

```yaml
brand: <品牌名>
queries_file: ./queries.yaml
created_at: <ISO timestamp>
planned_llms: [Kimi, 豆包, DeepSeek]        # 开局声明,只在第一次 probe 时问
completed:                                   # 每跑完一个 probe 就追加
  - {llm: Kimi, file: ./probe-results-kimi-..., probed_at: ...}
custom_llms: []                              # 自定义 LLM 的 name/url/notes
# pending = planned_llms - [c.llm for c in completed]  # 推导,不存
```

**为什么需要**：bambulab 案例暴露的根因——计划测的 LLM 列表只在用户脑子里，没文件记，analyze 阶段无法对账，漏跑一个就静默漏一个。这个文件把"全局计划"持久化，让 probe 跑完报进度、analyze 启动先对账、harness 直接基于它编排。

**所有 skill 的同目录假设**：queries.yaml / probe-plan.yaml / probe-results-*.yaml / analysis.md 都在同一目录（叫"测试目录"）。geo-probe 和 geo-analyze 都已硬编码这一点。

## 已完成

- [x] **模块 1：`geo-queries`** — 给定品牌信息（品牌名 / 行业 / 垂类 / 一句话定位 / 竞品），生成 30 条 GEO 测试问题，按 6 类意图分布（含「品牌识别」类）、长短风格混合。
      → `skills/geo-queries/SKILL.md`

- [x] **模块 2：`geo-probe`** — 拿 `geo-queries` 出的问题清单去问真实 LLM（内置 6 个预设 + 支持自定义），用 agent 自己的浏览器工具，每条之间随机间隔 20-60 秒防风控，记下回答 + 命中的品牌 + 引用源。q001-q005 是品牌识别类，跑完会有中场汇报。
      → `skills/geo-probe/SKILL.md` + `skills/geo-probe/probe.py`（仅 stdlib，机械活专用）

- [x] **模块 3：`geo-analyze`** — 把 probe-results 算成 visibility 分数（40/30/20/10 加权: 自然提及/识别/排名/情绪）、识别率、自然提及率、平均排名、竞品分布、引用源 top 域名、高价值零命中清单。输出 `analysis-<brand>-<date>.md` 供 geo-report 消费。纯 skill。
      → `skills/geo-analyze/SKILL.md`

## 进行中

（暂无）

## 待定（按顺序）
- [ ] **模块 4：`geo-report`** — 渲染一份给用户看的 markdown 报告（参考 Topify 那份的结构：总览 / 竞品对比 / 各平台分布 / 高价值零命中 prompt）。
- [ ] **模块 5（拼合）：`geo-harness`** — 串起前 4 个的总入口 skill。用户一句话触发整条流程，每个 checkpoint 都要用户确认才进下一步。**基于 `probe-plan.yaml` 编排**——不重新设计状态机；harness 只是按 plan 调度 probe 多次 + 一次 analyze + 一次 report，并在每个阶段间走用户确认门。

每做完一个模块都先单独跑通，再拼下一个。
