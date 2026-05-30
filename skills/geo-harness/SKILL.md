---
name: geo-harness
description: GEO 测试 harness 总入口。串起 geo-queries / geo-probe(每个 LLM 调一次)/ geo-analyze / geo-report / geo-channels 五个模块,**一句话触发,每个 checkpoint 都走用户确认门**。基于 probe-plan.yaml 编排,不引入新状态文件。**支持断点续跑**——从测试目录现有文件状态推断当前阶段,接着跑。
triggers:
  - 测我品牌的 AI 可见度
  - 跑一次完整 GEO 测试
  - GEO harness
  - 端到端 GEO 分析
  - geo-harness
  - 接着跑那个品牌的 GEO 测试
metadata:
  author: KnightMafiaLau
  source: geo-harness v0.1
user-invocable: true
disable-model-invocation: false
---

# geo-harness — GEO 测试 harness 总入口编排

## 什么时候用

用户想跑**一次完整端到端 GEO 分析**(从品牌信息 → 30 条 query → 多 LLM probe → analyze → 决策报告 → 投放建议),又**不想自己逐个调** geo-queries / geo-probe / geo-analyze / geo-report / geo-channels 五个 skill。

**也支持**:接续之前测过一半的品牌(从断点续跑)。

## 你（Claude）要做的事

### 1. 先判断"新跑"还是"续跑"

问用户:**"是新品牌测试,还是接续跑之前某个品牌?"**

- **新跑**:
  - 问品牌名 → 建议测试目录 `./<brand-slug>/`(用户可改)
  - 进入第 2 步(Phase 1 准备)
- **续跑**:
  - 问测试目录路径
  - 进入"断点检测"(见第 7 步)
  - 根据现有文件状态推断当前阶段,接着从该阶段跑

### 2. 前置检查(开跑前必须确认)

1. **浏览器工具可用**:probe 阶段需要 Claude-in-Chrome / 其他浏览器 MCP。**没有就停下报错**——不能跳过 probe(没真实数据 = 全套报告白做)
2. **canonical probe.py 同步**:开 probe 前 `cp ~/.claude/skills/geo-probe/probe.py <测试目录>/probe.py`(geo-probe 第 1.0 步已要求)
3. **测试目录可写**:`mkdir -p` 创建,验证可写

### 3. 流程概览(6 个 phase + 5 个 checkpoint)

```
Phase 1: 拿品牌信息 → 调 geo-queries → queries.yaml
         ↓ Checkpoint 1: 用户审 queries(可改/删/加)
Phase 2: 问 planned LLMs → 写 probe-plan.yaml
         ↓ Checkpoint 2: 用户确认 plan(N 个 LLM × 估计 N×20-30 分钟)
Phase 3: 对每个 planned LLM 调 geo-probe(N 次)
         ↓ Checkpoint per-LLM: probe 内部 q005 中场汇报 + probe.py verify-log 异常报警
         ↓ Checkpoint 全部 probe 完: plan 进度报"齐了,进 analyze"
Phase 4: 调 geo-analyze → analysis-<brand>-<date>.md
         ↓ Checkpoint 4: 用户看 analysis 顶层数(visibility / 头号竞品 / 零命中数)
Phase 5: 调 geo-report → report.md + report.html
         ↓ Checkpoint 5: 用户看 report(浏览器 open .html)
Phase 6: 调 geo-channels → channels.md + channels.html
         ↓ 完成:产物清单 + 一句话总结
```

**所有 sub-skill 调用通过 `Skill` tool**(`skill: geo-queries` / `skill: geo-probe` 等),不要自己复制其内部逻辑——保持模块独立性。

### 4. Phase 1 — geo-queries(出 30 条问题)

#### 4.1 拿品牌信息(5 项)

直接调 `geo-queries` skill,它会问用户:
- 品牌名(中文)
- 行业
- 垂类
- 一句话定位
- 竞品(2-3 个)

skill 会出 queries.yaml 到当前 cwd。**确保 cwd 是测试目录**(`cd <测试目录>` 或显式传 `--output`)。

#### 4.2 Checkpoint 1:用户审 queries

geo-queries 自带"出完跟用户确认"环节。**等用户改完 / 确认完后才进 Phase 2**。

### 5. Phase 2 — 创建 probe-plan.yaml

geo-probe 第 1.2 节自带"首次跑→问 planned_llms→建 plan"逻辑。但 harness 模式下用户对"完整流程"有预期,**harness 直接问 planned_llms,自己写 plan.yaml**:

> 准备测试 **<品牌名>** 的 GEO 可见度。**计划测哪几个 LLM?**
> 预设可选:Kimi / 豆包 / DeepSeek / 百度文心 / 千问 / 元宝
> 也可加自定义 LLM(给 name + url)
> 推荐:**Qwen + DeepSeek**(国内主流 + 数据收敛性好,2 个 LLM ~40-60 分钟)
> 完整覆盖:加上 Kimi 共 3 个(~60-90 分钟)

写 probe-plan.yaml 到测试目录,格式见 TASKS.md。

**Checkpoint 2:** 跟用户确认:

> 准备开跑:
> - 品牌:**<X>**
> - 测试目录:**<path>**
> - 计划 LLM:**<list>**(N 个)
> - 估计耗时:**N × 20-30 分钟 = <total> 分钟**
> - 30 条 query × N 个 LLM = **<N> 条 probe 任务**
> - 中间需要:用户登录各 LLM 账号(豆包必须;DeepSeek/Qwen/Kimi 推荐登录拿满 quota)
>
> 确认开跑吗?(y/n)

用户点头才进 Phase 3。

### 6. Phase 3 — 对每个 planned LLM 调 geo-probe

**循环**:对 plan.planned_llms 里 pending 状态的每个 LLM:

1. 调 `geo-probe` skill,传 `--llm <name>` 和测试目录
2. geo-probe 内部走完 30 条 query(q001-q005 中场汇报 + q006-q030 主循环 + 跑完 verify-log + 更新 plan.completed)
3. **harness 不打断 probe 内部流程**——probe 自己处理 query-level checkpoint
4. 一个 LLM 跑完,harness 报:
   > Probe 完成: **<LLM>**(<M>/<N> LLM 已完成)
   > - 命中 <X> 条 query / 引用 <Y> 个 URL
   > - verify-log: <pass / 有 K 条 anomaly>
   >
   > 继续跑下一个 LLM(<next LLM>)?(y/n,n 就暂停整个 harness)
5. 用户点头 → 下一个;n → 整个 harness 暂停,告诉用户"剩 <pending> 没跑,下次说'接续跑 <品牌>'即可续跑"

**所有 LLM 跑完**:

> 所有 probe 完成:**<N>/<N> LLM**
> - 总 query 数: <N × 30>
> - 总 URL 数: <X>
> - verify-log 全部 pass: <Y/N>
>
> 进入 analyze 阶段?(y/n)

### 7. Phase 4 — geo-analyze

调 `geo-analyze` skill,传测试目录。skill 内部:
- 读 probe-plan.yaml 对账(plan.pending 必须为空才进)
- 读所有 probe-results-*.yaml
- 算指标 + 出 analysis-<brand>-<date>.md

完成后:

> Analyze 完成:`analysis-<brand>-<date>.md`
> - Overall Visibility: <X>/100
> - 头号竞品: <X>(命中 N/M)
> - 高价值零命中: <K> 条
>
> 进入 report 阶段?(y/n)

### 8. Phase 5 — geo-report

调 `geo-report` skill,传 analysis 路径。skill 出 `report-<brand>-<date>.md` + `.html`。

完成后**自动 `open <html>`**(macOS):

> Report 完成:
> - `<path>/report-<brand>-<date>.md`
> - `<path>/report-<brand>-<date>.html`(已在浏览器打开)
>
> 进入 channels 阶段(投放建议)?(y/n)

### 9. Phase 6 — geo-channels

调 `geo-channels` skill,传 analysis 路径。skill 出 `channels-<brand>-<date>.md` + `.html`。

完成后**自动 `open <html>`**:

> Channels 完成:
> - `<path>/channels-<brand>-<date>.md`
> - `<path>/channels-<brand>-<date>.html`(已在浏览器打开)

### 10. 完成:产物清单 + 总结

> ✓ GEO harness 跑完。测试目录:`<path>`
>
> **核心产物**:
> - `queries.yaml`(30 条问题)
> - `probe-plan.yaml`(测试账本)
> - `probe-results-*.yaml`(<N> 份)+ `probe-log-*.jsonl`
> - `analysis-<brand>-<date>.md`
> - `report-<brand>-<date>.{md,html}`(决策人看)
> - `channels-<brand>-<date>.{md,html}`(投放团队看)
>
> **一句话结论**:<品牌> Visibility <X>/100,头号压力 <竞品 X>,优先投放 <top channel 1, 2>。详见 channels 报告。

### 11. 断点续跑:从文件状态推断阶段

用户说"接续跑 <品牌>" → 进测试目录,按下表推断当前阶段:

| 现有文件 | 缺失 | 推断阶段 | 接续动作 |
|---|---|---|---|
| 无 | 全部 | 未开始 | 从 Phase 1 开始 |
| queries.yaml | probe-plan.yaml | Phase 1 完 | 进 Phase 2 |
| queries + plan | 任何 probe-results | Phase 2 完 | 进 Phase 3 |
| plan + 部分 probe-results | plan.pending 非空 | Phase 3 中(部分 LLM 完成) | 继续跑 pending LLM |
| plan + 全 probe-results | analysis.md | Phase 3 完 | 进 Phase 4 |
| analysis.md | report.md / .html | Phase 4 完 | 进 Phase 5 |
| report | channels | Phase 5 完 | 进 Phase 6 |
| 全齐 | — | Phase 6 完 | 报"已完成,要不要重跑某阶段?" |

**报给用户当前状态 + 接续选项**:

> 接续 **<品牌>** 测试:
> - 当前阶段: Phase 3(probe)
> - 进度: <M>/<N> LLM 已完成(剩 <pending>)
> - 测试目录: <path>
>
> 接续动作:
> - 继续跑剩下的 <pending>(推荐)
> - 回退到 Phase 2 改 planned_llms
> - 跳到 Phase 4 用现有 partial 数据 analyze
>
> 怎么处理?

### 12. 失败处理

任何 sub-skill 失败 → harness 停下,报错给用户,**绝不自动重试**:

> Phase <N>(<skill>)失败:<具体错误>
> 当前状态已保存(`<plan + 已完成文件>`)。
>
> 你想:
> - 重试这个 phase
> - 跳过 + 标记 partial 继续
> - 整个 harness 在这停掉(下次接续)

### 13. 高级选项(用户可选传)

- `--skip-channels`:跑到 report 就停,不出 channels
- `--skip-report`:跑到 analyze 就停(给开发/调试用)
- `--llm-only <name>`:在已有 plan 基础上,只跑这一个 LLM(用于补漏)
- `--dry-run`:不真的 probe,只输出 plan + 估计耗时

默认全跑全产出。

### 14. 测试目录命名约定(同目录假设)

- 默认:`./<brand-slug>/`(slug = 品牌小写 ASCII,无空格)
- 用户可改,但 harness 一旦认定测试目录,**全程不变**——所有产物都落在这一个目录
- 已有目录 → 提示用户:"这个目录已有 <files>,接续跑吗?"

### 15. checkpoint 间隔的"分寸"

- **不要每个 sub-step 都问** —— probe 内部的 q005 中场汇报、verify-log 报警等是 probe skill 自己处理的,harness 不重复问
- **只在 phase boundary 问 y/n** —— 即 5 个核心 checkpoint
- **同一 phase 内不分多次确认** —— 如 Phase 3 跑 3 个 LLM,每个 LLM 完成后只问"继续下一个吗",不要在 LLM 内部再问

---

## 几个常见坑(别踩)

- **不要复制 sub-skill 逻辑** —— 全部通过 `Skill` tool 调,保持模块独立
- **不要静默自动重试** —— 失败必须报给用户决定
- **不要并行跑多个 LLM 的 probe** —— 浏览器同时操作多 tab 会乱;按 plan 顺序逐个跑
- **不要在 probe 阶段提前 analyze** —— plan.pending 非空时 analyze 会拿 partial 数据,会污染下游
- **不要假设用户会一次跑完** —— 必须支持断点续跑(基于文件状态推断,不引新状态文件)
- **不要忽略测试目录假设** —— 同目录是 probe/analyze/report/channels 全部硬约束,harness 不能跨目录操作

---

## 不做的事

- 不自己实现 queries 生成 / probe 抓取 / analyze 计算 / report 渲染 / channels 投放分析 —— 全部委托给对应 sub-skill
- 不修改 sub-skill 的内部逻辑(不传命令行 hack 覆盖 sub-skill 行为)
- 不引入新状态文件(probe-plan.yaml 是 single source of truth)
- 不并行 probe 多个 LLM
- 不在数据不全(plan.pending 非空)时静默跳到 analyze
- 不在 probe 阶段失败时自动重试(必须问用户)
- 不假装数据齐全(partial 状态严格传递到下游 analyze + report + channels)
