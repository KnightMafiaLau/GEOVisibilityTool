---
name: geo-channels
description: 给一份 analysis-<brand>-<date>.md（geo-analyze 的输出，可选 + report-<brand>-<date>.md），渲染一份 actionable 的 GEO 渠道投放建议报告。**双输出**:`channels-<brand>-<date>.md` + `.html`(自包含、内嵌作者水印)。**Topify-CEO 风格,紧急/长期分流**:负面信号 → 紧急处理(红色专区);优先 channel 投放清单 → top 10 grid + 内容形态建议;per-LLM 适配 → 内容+渠道双维度;竞品反位 + 零命中攻关。**ROI 定性 high/med/low,公式公开,无伪精度**。
triggers:
  - GEO 投放建议
  - 渠道投放清单
  - 该投哪里
  - channel report
  - 投放策略
  - geo-channels
  - 出 channel 报告
metadata:
  author: KnightMafiaLau
  source: geo-harness v0.1
user-invocable: true
disable-model-invocation: false
---

# geo-channels — GEO 渠道投放建议(actionable layer)

## 什么时候用

用户跑完 `geo-analyze` + `geo-report`,拿到了诊断数据(visibility / 竞品 / channel),想知道 **"该往哪投、为什么投、什么内容形态、紧急还是长期"**。

**与 geo-report 的边界**:

| geo-report | geo-channels(本模块) |
|---|---|
| **诊断**:visibility 分数 / 报忧报喜 | **处方**:每个发现对应"该投哪里 + 什么内容形态 + ROI 定级" |
| CEO / 决策人视角 | 投放团队 / 内容团队 / CMO 视角 |
| 描述"是什么 / 为什么这样" | 描述"该做什么 / 优先做什么 / 怎么做" |
| 不出建议 | **唯一出建议的模块** |

## 你（Claude）要做的事

### 1. 拿输入

1. **analysis-<brand>-<date>.md 路径**(必填,source-of-truth)
2. **report-<brand>-<date>.md 路径**(可选,用于叙述风格一致性 + 报忧报喜对齐)
3. **输出路径**——默认 `<同目录>/channels-<brand>-<date>.{md,html}`

### 2. 读输入 + 校验

- ✓ analysis frontmatter 必须有 `brand` / `llms_analyzed` / `partial` / `missing_llms`
- ✓ 必须有 引用源 channel 表(`top 15 域名`)+ per-LLM × per-intent 矩阵
- ✓ 竞品分布表 必须有
- ✓ 高价值零命中清单(可选,本节产出依赖它)
- ✓ `partial: true` → 顶部红 banner(继承 report 模式)

### 3. 风格定调:同 geo-report(CEO 视角 + 数据密集 + 极少叙述)

**与 report 同**:
- Hero 卡片 + heatmap 颜色编码 + 极少叙述
- 每节解读 ≤ 100 字(通常 1-2 行 kicker 注脚)
- 不用感叹号 / 委婉副词
- 不写"方法学说明"

**channels 特有**:
- 用 **"紧急 / 中期 / 长期"** 三级时间维度替代"高/中/低 ROI"——更符合执行 timeline
- 用 **"投放形态 pill"** 标记每个 channel 该发什么(深度文 / 视频 / 评测 / 问答 / 行业稿 / 专利等)
- 每条建议必须有 **数据支撑**(引用 analysis 里的具体数字)

### 4. 报告结构(7 节固定)

#### 节 1 — Header

- 标题:`GEO 渠道投放建议:<品牌名>`
- 副标题:`基于 <LLM 列表> 的 N 条响应分析 · 共 K 条 actionable 建议`

#### 节 2 — Hero metrics(3 卡片 grid)

| 卡片 | 内容 |
|---|---|
| **紧急处理项** | 大数字(N 条)+ 定性 pill(`紧急 critical` / `观察 watch` / `无 none`) |
| **优先攻关 channel** | top N 投放 channel 数 + per-platform 分布(DeepSeek X 个 / Qwen Y 个) |
| **零命中攻关 query** | 待补内容 query 数 + 商业意图分布(选型 X / 采购 Y / 对比 Z) |

#### 节 3 — 🔥 紧急处理:负面信号 / 误识别(独立红色专区,**top priority**)

**触发条件**(任一即触发):
- analysis 里 `target_brand.sentiment === 'negative'` 的 query ≥ 1
- 品牌识别 q001-q005 中 `status_label === 'misidentified'`(误识别为同名公司)
- 竞品对位中 target 被显著贬低(rank > 竞品 2+ 位 + sentiment negative)

**没触发**:写一段 note "本次未发现负面信号 / 误识别。**持续巡查**——下次 probe 若出现,自动触发本节红色专区"。

**触发了**:红框红字,**每条独立列出**:

```
[query_id] <intent 类> — <query 文本>
平台: <LLM>
当前状况: <evidence 原句>
攻关方向: <该往哪发 + 内容形态 + 优先级>
处理 timeline: <立即 / 7 天内 / 30 天内>
```

紧急处理**不与其他节合并**,因为 reputation damage 的修复 timeline 比 channel 投放紧得多(damage 在公开 LLM 端持续累积)。

#### 节 4 — 优先 channel 投放清单(top 10 grid)

5 列 grid 卡片(同 report 竞品对比卡)。每张:

- 域名 (主标题)
- **ROI 定性 pill**(`高 high` / `中 med` / `低 low`)
- **投放形态 pill**(深度文 / 视频 / 评测 / 问答 / 行业稿 / 专利 等)
- **关键数据**:appearance 次数 + cross-LLM 覆盖 + 主要 intent
- **一句话理由**(≤ 30 字,引数据)

**ROI 定性判断**(写在 grid 后 kicker 注脚里):

```
高 ROI:appearance ≥ 5 AND (cross-LLM OR 覆盖 ≥ 3 个 intent)
中 ROI:单 LLM 但 appearance ≥ 5,或 跨 LLM 但 appearance < 5
低 ROI:单 LLM + appearance < 5(但仍 > 1)
```

**投放形态 mapping**(必背):

| 域名类型 | 形态 |
|---|---|
| 知乎专栏 (zhuanlan.zhihu.com) | 长文深度评测 |
| 知乎问答 (zhihu.com/question) | Q&A 高赞答案 |
| 36氪 / 澎湃 / 界面 / 财联社 | 行业稿 / 投融资稿 |
| smzdm / 什么值得买 | 购买决策 / 性价比测评 |
| B站 / bilibili | 视频测评 |
| 微信公众号 / 搜狐自媒体 | 自媒体长文 |
| 谷歌专利 / patents.google | 专利申请 + 技术解析 |
| 雪球 / xueqiu | 财经分析 |
| 行业垂直站(3druck / mohou / hyg3d / raise3d 等) | 垂直行业评测 |
| pcmag / pconline / it168 等科技评测站 | 通用科技评测 |
| 百科 (zh.wikipedia / baike.baidu) | 词条建设 |
| 政府 / 学术 (gov.cn / edu.cn / .ac.cn) | 政策稿 / 案例稿 |
| 招聘库 (jobmob / boss直聘) | 公司词条建设 |
| 视频站 (b23.tv / 抖音) | 短视频测评 |

未在 mapping 里的,根据域名性质判断(行业站 / 综合媒体 / 评测 / 财经),给最贴近的形态。

#### 节 5 — Per-LLM 适配策略(内容喜好 + 渠道喜好 双维度)

按 LLM 分小节,每个 LLM 一张表:

| 维度 | 该 LLM 偏好 | 投放重点 |
|---|---|---|
| **内容形态偏好** | 文字深度 / 视频 / 评测 / 技术 / 财经 等(从 analysis §6.5 推) | 该往哪个形态发力 |
| **核心 channel 偏好** | top 3-5 域名(从 analysis §6.1 + 该 LLM 列) | 优先投放清单 |
| **强 intent 偏好** | 哪些 intent 该 LLM 引用源最密 | 投放重点 intent |
| **特异性信号 ⚠** | 反常识但极强的偏好(如 Qwen 查 Google Patents) | 针对性内容形态 |

(如 Qwen 在了解原理类查谷歌专利 → "可考虑申请技术专利 + 在专利文档里嵌入品牌叙述,捕获 Qwen 该类问题的命中")

#### 节 6 — 竞品反位攻关(独立专区,**channels 比 report 多的核心洞察**)

按"被竞品占位的 case"列,每条独立 block:

```
[case 编号] 竞品 X 在 <LLM> 的 <intent> 类引用了 <domain>(竞品官网/内容)
位置: <具体哪几条 query>
影响: <竞品在该 intent 的位次 + sentiment;target 的对应表现>
反位建议:
  - 短期:在 <竞品占位的 channel 同类> 上发对位内容
  - 中期:推动 target 官网在该 channel 的同类 query 中入选
  - 长期:占据该 intent 的"品牌词条"信源
```

**典型场景**:
- "DeepSeek 选型类引 creality.com" → bambulab 官网在该 LLM 选型类信源未入池 → 反位:推 bambulab.com 内容入 LLM 知识库 + smzdm/36氪 投评测对位稿
- "Qwen 对比类引 elegoo.com.cn" → 同上,但 Qwen 偏知乎深度文 + B 站视频 → 反位重点投这两类

**没有反位 case**(竞品官网/内容未占位):写 "本次未发现竞品 channel 占位,持续巡查"。

#### 节 7 — 零命中 query 攻关(每条独立 block)

**触发**:analysis 里的"高价值零命中清单"(满足"商业意图 + 竞品占位 + 自身缺席"的 query)。

每条:

```
[query_id] <intent> — <query 文本>
缺席平台: <LLM 列表>
该 query 上占位竞品: <竞品 + 各自 rank>
攻关方向:
  - 优先 channel:<top 1-2 channels — 引用源画像里该 intent 的高频域名>
  - 内容形态:<根据 channel 类型,从节 4 mapping 取>
  - 必须包含的关键词/数据点:<从 query 文本里抽取的具体诉求,如"4000 元预算""PLA 速度""新手"等>
  - 优先级:<紧急 / 中期 / 长期>
```

样本不足(本次只 6 条 query)时,写 "本次抽样不足以筛真零命中,需补完整 30 条 probe;本节留空待补"。

### 5. HTML 模板(canonical,与 report 共享 CSS,只加 channels 特异 class)

复用 geo-report 的 CSS,**加 channels 专属 class**:

```css
/* === 紧急专区 === */
.urgent-block {
  background: #fff5f5; border: 2px solid #dc3545;
  padding: 1em 1.2em; margin: 1em 0;
  border-radius: 6px;
}
.urgent-block h3 { color: #b02838; margin: 0 0 0.5em 0; }
.urgent-item { border-top: 1px solid #f5c2c7; padding: 0.6em 0; }
.urgent-item:first-of-type { border-top: none; }

/* === ROI/形态 pill === */
.roi-pill, .format-pill {
  display: inline-block; padding: 0.15em 0.6em;
  border-radius: 10px; font-size: 0.75em; font-weight: 600;
  margin-right: 0.3em;
}
.roi-high { background: #d4edda; color: #155724; }
.roi-med  { background: #fff3cd; color: #856404; }
.roi-low  { background: #f8d7da; color: #721c24; }
.format-pill { background: #e8eaf6; color: #283593; }

/* === Channel 卡片(复用 comp-card,但加 ROI/形态 显示) === */
.channel-card .reason { font-size: 0.78em; color: #555; margin-top: 0.4em; line-height: 1.3; }
```

Hero 卡片 / 表格 heatmap / 报忧报喜 / 水印 等全部沿用 geo-report 的 CSS。

### 6. 验证 HTML 自包含

- ✓ `body::before` 保留(水印)
- ✓ 水印文本 `geo-harness · KnightMafiaLau` 存在
- ✓ 没有 `<link>` / `<script src>`

### 7. 水印红线

同 geo-report,完全一致。

### 8. 写完后跟用户确认

> 投放建议已生成:
> - `<path>.md` — 文本版
> - `<path>.html` — Topify-style HTML,可双击浏览器打开
>
> 顶层结论:
> - <如果 partial>**⚠️ 基于不完整数据**</如果>
> - 紧急处理项:<N> 条(<critical/watch/none>)
> - 优先攻关 channel:top <N>(高 ROI <X> / 中 ROI <Y> / 低 ROI <Z>)
> - 零命中攻关 query:<N> 条
> - 竞品反位 case:<N> 个
>
> 投放团队拿这份,可以按 timeline 排期。

---

## 几个常见坑(别踩)

- **不要给"具体标题 / 数据点 / 文章框架"** — 那是内容团队的活,channels 给到"该往哪发 + 什么形态 + 关键诉求"就停
- **不要算定量 ROI 打分** — 定性 high/med/low + 公开公式 就够;定量会装且伪精度(数据是抽样)
- **紧急专区无触发条件时也要写一段** — 写"本次未触发,持续巡查"而非省略;**让用户每次报告都看到"这一节存在"**,负面信号下次来时不会被遗漏
- **per-LLM 适配必须双维度**(内容形态 + 渠道偏好) — 单维度无法行动
- **零命中清单不能编** — 如果 analysis 里没真零命中(只有结构性 q011),本节就写"样本不足待补"
- **不要拆出"投放预算 / 投放 KPI / 投放团队分工"等** — 超出 GEO 边界,这是 marketing ops 的活

---

## 不做的事

- 不读 probe-results 原始数据 — 只读 analysis.md (+ optional report.md)
- 不重算指标 — 从 analysis 抄
- 不写营销文案 / 品牌吹捧 / 情绪化语句
- 不出"投放预算 / KPI / 团队分工 / 排期甘特图"——超出 GEO 边界
- 不出具体内容 brief(标题 / 数据点 / 框架)——内容团队的事
- 不在 partial 模式下假装数据完整
- **不去掉 / 改文本 / 替换水印**
- 不省略 .md 末尾的署名行
- 不调外部 markdown-to-html 工具 — 必须 Edit/Write 手写
- 不省略"紧急处理"节即使无触发——必须写"本次未触发"让节存在
