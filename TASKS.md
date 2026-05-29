# Tasks

最终目标：把所有模块装成一个 GEO 测试 harness。

## 已完成

- [x] **模块 1：`geo-queries`** — 给定品牌信息（品牌名 / 行业 / 垂类 / 一句话定位 / 竞品），生成 30 条 GEO 测试问题，按 6 类意图分布（含「品牌识别」类）、长短风格混合。
      → `skills/geo-queries/SKILL.md`

- [x] **模块 2：`geo-probe`** — 拿 `geo-queries` 出的问题清单去问真实 LLM（内置 6 个预设 + 支持自定义），用 agent 自己的浏览器工具，每条之间随机间隔 20-60 秒防风控，记下回答 + 命中的品牌 + 引用源。
      → `skills/geo-probe/SKILL.md` + `skills/geo-probe/probe.py`（仅 stdlib，机械活专用）

## 进行中

（暂无）

## 待定（按顺序）
- [ ] **模块 3：`geo-analyze`** — 把 `geo-probe` 的原始数据算成 visibility 分数、平均排名、命中分布、零命中机会清单。
- [ ] **模块 4：`geo-report`** — 渲染一份给用户看的 markdown 报告（参考 Topify 那份的结构：总览 / 竞品对比 / 各平台分布 / 高价值零命中 prompt）。
- [ ] **模块 5（拼合）：`geo-harness`** — 串起前 4 个的总入口 skill。用户一句话触发整条流程，每个 checkpoint 都要用户确认才进下一步。

每做完一个模块都先单独跑通，再拼下一个。
