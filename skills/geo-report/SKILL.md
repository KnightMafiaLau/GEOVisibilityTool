---
name: geo-report
description: 给一份 analysis-<brand>-<date>.md（geo-analyze 的输出），渲染一份给决策人看的对外可读报告。**双输出**:`report-<brand>-<date>.md` + `report-<brand>-<date>.html`(自包含、内嵌作者水印、要 PDF 浏览器 Cmd+P 自存)。顾问咨询语调,7 节结构,partial 模式强红 banner,竞品反向估算对比表(只比单维指标、不造合成分),per LLM × per intent 引用源偏好诊断。不出"下一步建议"——那是 geo-channels 的事。纯 skill。
triggers:
  - 出 GEO 报告
  - 生成可见度报告
  - 把 analysis 写成对外报告
  - geo-report
  - 渲染 visibility 报告
metadata:
  author: KnightMafiaLau
  source: geo-harness v0.1
user-invocable: true
disable-model-invocation: false
---

# geo-report — 把 analysis 渲染成给人看的对外报告

## 什么时候用

用户跑完 `geo-analyze`，拿到了 `analysis-<brand>-<date>.md`，想要一份能直接拿去给决策人 / 内部团队 / 客户看的可读报告。

**与 analysis.md 的边界**:

| analysis.md(模块 3 出) | report.md(本模块出) |
|---|---|
| 数据 + 表格 + 清单 | 叙述 + 解读 + 横向对比 |
| 说"是什么"——分数 / 排名 / 缺口 | 说"所以呢"——意味着什么、谁压着你、缺在哪 |
| 中性、机器可读 | 顾问咨询语调,决策人可读 |

**本 skill 不出"下一步建议 / 投放方案"**——那是后续 `geo-channels` 模块的事(在 v2 里还未整合,先留出边界)。

## 你（Claude）要做的事

### 1. 拿输入

1. **analysis-<brand>-<date>.md 路径**(必填)
2. **输出路径**——默认 `<同目录>/report-<brand>-<date>.md`,用户可改
3. **目标读者**(可选,影响语调的微调):
   - `internal`(自己/团队看)——默认
   - `client`(交付给品牌客户看)——语气更克制,标记"建议"段落改成"观察"
   - `exec`(决策人/老板看)——TL;DR 加长,后面节都精简

### 2. 读 analysis.md + 校验

用 `Read` 工具读 analysis.md,做基本校验:

- ✓ frontmatter 必须有 `brand` / `analyzed_at` / `llms_analyzed` / `partial` / `missing_llms`
- ✓ 必须有 Overall 段 + Per-LLM 段 + 品牌识别细节 + 竞品分布 + 引用源 + 高价值零命中清单 + 数据完整性
- ✓ 如果 `analysis_version` 不是 `v1`,停下问用户:"analysis 是更新版本,我可能漏字段,要继续吗?"
- ✓ **特别注意 `partial: true`**——这会触发顶部红色 banner(见第 4 步)

### 3. 风格定调:顾问咨询语调

整份报告**用顾问咨询的语气写**——克制、数据驱动、不夸张、不卖惨。

**对比示例**:

| ❌ 冷峻直白(不要这种) | ❌ 营销文案(更不要) | ✅ 顾问咨询(要这种) |
|---|---|---|
| "你的品牌在 Kimi 上几乎不存在" | "拓竹品牌力强劲,行业领先" | "目标品牌在 Kimi 端的识别强度处于较低区间,识别率为 0%,即模型在当前知识截止内未将该品牌纳入主动召回范围" |
| "智元把你按在地上摩擦" | "竞品分析显示拓竹具有独特优势" | "竞争格局上,智元在 22/25 条自然提及类问题中被点名,平均排名 1.3,构成当前的主要可见度压力" |
| "30% 太差了" | "整体表现可圈可点" | "Visibility Score 30/100,对应"待建设"区间(见评分参考)" |

**口径**:
- 用"较低 / 较弱 / 偏弱"代替"差 / 不行 / 失败"
- 用"建设空间 / 待优化 / 暂未覆盖"代替"缺 / 没有 / 漏"
- 用"压力 / 拉开差距 / 占位"代替"碾压 / 吊打"
- 不出感叹号
- **但**:数字本身一定要直白,不打哑谜("识别率 0%" 就写 0%,不写"识别率有待提升")

### 4. partial 模式:顶部红 banner(强提醒)

如果 analysis.md 的 frontmatter 有 `partial: true`,**在标题正下方第一段**插入:

```markdown
> ⚠️ **本报告基于不完整数据**
>
> 计划测试 LLM: <planned 列表>
> 实际完成: <completed 列表>
> **缺失**: <missing_llms 列表>
>
> 所有分数、排名、零命中清单均按现有 N 份 probe 数据计算,**不能代表整体可见度**。建议在补齐缺失 LLM 后重新生成报告。
```

**这个 banner 不允许省略、不允许折叠、不允许放到末尾**——藏起来 = 撒谎。

### 5. 渲染报告:7 节结构

按下面 7 节写(顺序固定,不要重排):

#### 节 1:TL;DR

3-5 行,给"打开报告读 30 秒就要走人"的决策人看:

- 总分(overall visibility score)+ 区间定性(见下面【评分参考】)
- 最强 LLM / 最弱 LLM
- 头号竞品压力
- 一句话定性结论:模型对该品牌的整体识别强度处于 X 区间

【评分参考】(报告里不展示这张表,你心里有数即可,用区间名定性):
- 80-100:**高可见度**——品牌已稳定建立 LLM 端记忆,持续维护即可
- 60-79:**中等可见度**——存在,但在关键品类问题中竞争位次有压力
- 40-59:**低可见度**——被识别但召回稀疏,需要系统性内容补强
- 20-39:**待建设**——零星出现,主要场景缺席
- 0-19:**未建设 / 待入场**——LLM 端基本不收录,需要从 0 起步

#### 节 2:可见度全景

- **overall + per-LLM 分数表格**(直接从 analysis 抄数,不重算)
- **指出最弱 LLM**(分数最低那个)+ 一句解读"该平台是当前的可见度短板"
- **指出最强 LLM**(分数最高那个)+ 一句解读"该平台是相对优势位"
- 如果某分量被排除(`排除分量: [...]`),写一段说明哪个数据缺失、为什么

#### 节 3:品牌识别状况

q001-q005 的横向健康度。展示形式:

- **状态分布饼**(用文字):N 条 recognized / M 条 not_recognized / K 条 misidentified
- **如有 misidentified**(误识别) → **特别拎出来单独写一段**,直接抄 notes 里的"串到了哪家公司"——这是 GEO 最关键的负面信号
- **每个 LLM 一行小结**:"Kimi 端: 5 条品牌识别中 0 条正确识别 / 3 条明确未收录 / 2 条误识别为某 X 公司"
- **定性**:0 收录 / 部分识别 / 高识别 三选一

#### 节 4:自然提及表现

**只展示 4 类有效 intent**:探索发现 / 选型推荐 / 了解原理 / 采购/投资。

**对比评估和品牌识别都不在此节**:
- **品牌识别**:已在节 2 单独呈现(识别率指标)
- **对比评估**:query 模板「A vs B」结构性排除 target,**算进 mention_rate 是把永远 0 命中的稀释项塞进分母**——人为压分且无法纠正。**这一类的数据用在节 4「竞品格局」(竞品同台对位的核心信号源)** ,不进本节命中率统计。在节 3 末尾加一句:"对比评估类由于 query 结构排除 target,作为竞品格局信号源在第 4 节呈现"

- **总数**:N/M 条自然提及命中(M = 4 类有效 intent 的 query 数)
- **按 intent 拆分**(从 analysis 的 per-intent 数据读):
  - 探索发现 类: N/M 命中(顶部行业问题里出现 vs 缺席)
  - 选型推荐 类: N/M 命中(**这是最商业的一类,单拎出来写一句**)
  - 了解原理 类: N/M 命中(普及类,命中本就低)
  - 采购/投资 类: N/M 命中
- **最强 intent / 最弱 intent**:哪类在自然语境下能被想到,哪类完全缺席
- **特例**:如果对比评估 query 里显式含 target 品牌名(如「拓竹 vs 创想」),那条计入正常 mention 统计;geo-analyze 已经按这个口径处理

#### 节 5:竞品格局 + **反向估算横向对比表**(用户要求加)

**核心横向对比表**(直接给冲击力):

| 品牌 | 自然提及率 | 出现 query 数 | 平均排名 | 正向情绪占比 |
|---|---|---|---|---|
| **<目标品牌>** (我) | <X>% | <N>/25 | <X> | <X>% |
| 智元 | 88% | 22/25 | 1.3 | 90% |
| 宇树 | 72% | 18/25 | 2.1 | 85% |
| ... | | | | |

**关于这张表的诚实声明**(写在表下方一行小字):

> 竞品的"自然提及率"等指标来自 analyze 阶段对 q006-q030 的反向统计,仅用于横向比较;由于本次 probe 未对各竞品做"品牌识别"专项问询(q001-q005 只问目标品牌),竞品的"识别率 / 情绪覆盖率"无法对等估计,因此本表**不构造竞品的合成 visibility 分数**,以免引入伪精度。

写完表 + 声明后,**用文字点出**:

- **头号压力源**:出现频次和排名最高的竞品 → 一句解读"在 X 类问题中占据 top N 位次"
- **次级竞品**:出现频次中等但有特定 LLM/intent 集中度的
- **意外露出**:出现的非主要竞品(用户没列进 competitors 但被模型自然召回的)→ **这是 analyze 已经做了的"其他品牌"列,这里挑 1-2 个有信号的**

#### 节 6:引用源画像(channel-level + article-level + intent 偏好)

**前提认知**:`citations` 字段是 URL 级数据(同域名多 URL 全保留,同 URL 多次出现也保留)。这一节有 **3 个子表**,各回答不同的投放策略问题:

**6.1 全局 top 15 域名(channel-level — 哪些站值得系统投放)**:

| 域名 | 总出现次数 | 不同 URL 数 | 覆盖比 | 渠道类型 | 主要 intent | 出现 LLM |
|---|---|---|---|---|---|---|
| smzdm.com | 18 | 14 | 0.78 | **广覆盖** | 选型/对比 | Kimi, DeepSeek |
| 36kr.com | 14 | 5 | 0.36 | 中度集中 | 探索/采购 | Kimi, 豆包 |
| zhihu.com | 12 | 2 | 0.17 | **单篇热文** | 选型推荐 | Kimi, DeepSeek |

**解读规则**(必须写进报告):
- **覆盖比 ≥ 0.6 / 渠道类型 = "广覆盖"** → 该站是 channel,模型在该站读过多篇不同内容。投放策略:系统性持续产内容,把这个站做成"高密度自有内容池"
- **覆盖比 < 0.3 / 渠道类型 = "单篇热文"** → 该站是 anchor,模型反复回头看的可能是某一篇高赞答案 / 测评。投放策略:**先去看 6.2 节那篇 URL 是什么**,反向工程它的角度+质量
- **中度集中**:两者之间,需要看具体 URL

不要只看域名 appearances 排名;**忽略覆盖比 = 把"系统投放"和"反向工程一篇文章"两种完全不同的策略混成一种**。

**6.2 高频 URL top 10(article-level — 哪些具体文章是 canonical source)**:

| URL | 域名 | 被引次数 | 出现于 query | 出现 LLM |
|---|---|---|---|---|
| https://zhihu.com/question/598234/answer/.. | zhihu.com | 8 | q006/q007/q012 | Kimi, DeepSeek |
| https://smzdm.com/p/3d-printer-2026-buy | smzdm.com | 5 | q008/q009 | Kimi |

**解读规则**(必须写进报告):这些是"垂类内 LLM 反复回头看的源",**是 GEO 反向工程的核心对象**——不是简单加自己的内容,而是分析"为什么是这一篇"(标题角度?数据点?发布平台?作者权威?发布时间?),然后:
- 复刻该角度但更深 / 更新
- 或想办法让自己被这一篇引用

如果 top 10 里 appearances 都 ≤ 1(分析阶段已标出),写一句"无明显 canonical URL,LLM 对每条 query 都搜不同内容,该垂类是广度型搜索行为,投放思路偏 6.1 而非反向工程"。

**6.3 各 LLM 在不同 intent 上的来源偏好(intent-channel 矩阵)**:

按 LLM 分小节,每个小节列该 LLM 在各 intent 类型下的 top 3-5 域名,**并标出每个域名下被引最多的具体 URL**。这一节是节 6.1(channel)和节 6.2(article)的 cross-tab。

**示例**(假设 Kimi):

> ##### Kimi
> - **探索发现 类**:36kr.com (8, hot: `36kr.com/p/2745881` × 3) / zhihu.com (5) / sohu.com (3) — 偏综合科技媒体 + 问答社区;36 氪那一篇是该类问题的 anchor
> - **选型推荐 类**:smzdm.com (10, hot: `smzdm.com/p/3d-printer-2026-buy` × 4) / bilibili.com (6) / chiphell.com (4) — 偏垂直评测;**那篇 smzdm 2026 选型攻略是 Kimi 该类问题的 canonical 引用,值得逐字研究角度**
> - **对比评估 类**:bilibili.com (5) / b23.tv (3) — 视频评测占主导
> - **了解原理 类**:csdn.net (2) — 数据稀疏,暂无明显偏好
> - **采购/投资 类**:36kr.com (5) / 投资界类站 (2) — 偏行业媒体
>
> **诊断**:Kimi 在选型决策类问题上**明显锚定 smzdm 单篇热文 + 垂直评测站**;要提升 Kimi 端选型问题命中,**先研究那篇 smzdm 攻略的角度和数据点**(article-level 反向工程),再考虑系统性投放 bilibili 测评 / chiphell 硬件社区(channel-level)。

(其余 LLM 同样格式,**逐个写**——**不允许偷懒只写 1-2 个 LLM**)

如果某 LLM 在某 intent 类引用源 < 3 条(数据稀疏),写"该 intent 数据稀疏,暂无明显偏好"。

#### 节 7:高价值零命中清单(top 10)

从 analysis 的"高价值零命中清单"原样过来,但**格式重写成报告风格**:

每条一段(不再用 list):

> **#1 选型推荐** — 做 RAG 知识库项目,初创团队选哪个向量库最省心?
> 在 Kimi / 豆包 / DeepSeek 三个平台均未触达本品牌。该 query 上 3 家竞品被点名推荐(智元 [Kimi rank 1] / 宇树 [Kimi rank 2] / 优必选 [豆包 rank 1])。**判断**:直接选型意图,商业价值高,竞品已系统性占位,是优先攻关方向。

**为什么 10 条都要展开写**:这一节是本报告里**最 actionable** 的部分(虽然不出"建议",但展开的 query 原文 + 竞品占位 + 缺席平台,已经把"该往哪发什么内容"的暗示给到极致),决策人和内容团队会一条条看。不要折叠、不要省略。

#### (节 8 留空 — 不出"下一步建议")

报告结束。**不写"接下来该怎么做""建议优先 X""推荐采取 Y 策略"这一类内容**——本模块边界严格止于诊断。投放建议是 `geo-channels` skill 的事。

可以在报告末尾加一行小字:

> 投放策略与渠道建议详见后续 `geo-channels` 报告。

### 5.5 报告 markdown 尾部强制加作者署名(不可删)

**不管语调怎样、不管谁是读者**,markdown 末尾**必须**加这一段(原样,不许改):

```markdown
---

<sub>本报告由 [geo-harness](https://github.com/KnightMafiaLau/geo-harness) 生成 · 作者: **KnightMafiaLau** · 同时附带带水印的 HTML 版本</sub>
```

用户可以在自己改的版本里把这段挪到别的位置,但**不能整段删**——这是 attribution 红线。

### 6. 同时生成 HTML 版本(内嵌水印,自包含)

**与 .md 同步**写一份 `report-<brand>-<date>.html`,放在同一目录。

为什么要 HTML 而不是 PDF:
- 不依赖系统工具(每台机器都有浏览器)
- 自包含一个文件(CSS 内嵌,没有外部依赖,可邮件转发)
- 用户要 PDF → 浏览器打开 → Cmd+P → 存为 PDF,水印照样保留

#### 6.1 HTML 模板(原样用,不许改 CSS 里的水印部分)

把这个模板填进去——`<title>` 和 `<main>` 替换成实际内容,**其它部分(尤其 `body::before` 那块水印 CSS)逐字保留**:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>GEO Visibility Report: <品牌名></title>
<style>
@page { margin: 2cm; size: A4; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  line-height: 1.7;
  max-width: 820px;
  margin: 0 auto;
  padding: 3em 2em;
  color: #222;
  background: #fff;
  position: relative;
  overflow-x: hidden;
}

/* === 作者水印:不可移除 === */
body::before {
  content: "geo-harness · KnightMafiaLau";
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(-30deg);
  font-size: 5em;
  font-weight: 800;
  color: rgba(0, 0, 0, 0.05);
  z-index: 0;
  white-space: nowrap;
  pointer-events: none;
  user-select: none;
  letter-spacing: 0.05em;
}
@media print {
  body::before {
    position: fixed;
    color: rgba(0, 0, 0, 0.06);
  }
}
/* === 水印结束 === */

main { position: relative; z-index: 1; }

h1 { font-size: 1.9em; border-bottom: 2px solid #333; padding-bottom: 0.3em; margin-top: 0; }
h2 { font-size: 1.4em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; margin-top: 2em; }
h3 { font-size: 1.15em; margin-top: 1.5em; }
h4, h5 { margin-top: 1.2em; }

table { border-collapse: collapse; margin: 1em 0; width: 100%; background: #fff; }
th, td { border: 1px solid #ddd; padding: 0.5em 0.8em; text-align: left; }
th { background: #f5f5f5; font-weight: 600; }

blockquote {
  border-left: 4px solid #ddd;
  padding: 0.5em 1em;
  margin: 1em 0;
  color: #555;
  background: #fafafa;
}

/* partial banner — 与水印同等优先级,不可省略 */
.partial-banner {
  background: #fff3cd;
  border: 2px solid #d9534f;
  padding: 1em 1.2em;
  margin: 1.5em 0;
  border-radius: 4px;
  color: #6e1f17;
}
.partial-banner strong { color: #a02414; }

code { background: #f4f4f4; padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.92em; }

footer {
  margin-top: 4em;
  padding-top: 1.5em;
  border-top: 1px solid #ccc;
  font-size: 0.85em;
  color: #666;
  text-align: center;
}
footer a { color: #555; }
</style>
</head>
<body>
<main>

<!-- 这里把 markdown 报告的内容渲染成 HTML -->
<!-- 7 节内容全部填进来,partial banner 如果有,用 <div class="partial-banner">...</div> -->

</main>

<footer>
本报告由 <a href="https://github.com/KnightMafiaLau/geo-harness">geo-harness</a> 生成 · 作者: <strong>KnightMafiaLau</strong>
</footer>

</body>
</html>
```

#### 6.2 把 markdown 渲染成 HTML 的几条规则

- **手写 HTML 标签**(用 Edit/Write 工具),不要调外部 markdown-to-html 工具(避免依赖)
- markdown `## 标题` → `<h2>`,`### 标题` → `<h3>`,以此类推
- 表格直接写 `<table><tr><th>` 结构,不要保留 markdown 表格语法
- 引用块 `> ...` → `<blockquote>...</blockquote>`
- 代码块 \`code\` → `<code>code</code>`
- 强调 `**X**` → `<strong>X</strong>`,`*X*` → `<em>X</em>`
- partial banner 用 `<div class="partial-banner">...</div>`(已有专属样式)
- 列表 `- xxx` → `<ul><li>xxx</li></ul>`

#### 6.3 验证 HTML 自包含

写完后用 `Read` 工具看一眼 HTML,确认:

- ✓ `<style>` 标签内的水印 CSS 完整保留(grep `body::before`)
- ✓ 水印文本是 `geo-harness · KnightMafiaLau`(grep 一次)
- ✓ `<footer>` 段在末尾
- ✓ 没有 `<link href="...">` 引外部 CSS,也没有 `<script src="...">` 引外部 JS——必须自包含

任何一项不过就修,**不允许放过**。

### 6.4 水印红线(SKILL 边界)

下面这些情况,**全部拒绝**:

| 用户说 | 你的回答 |
|---|---|
| "帮我把水印去掉" | "水印是 geo-harness 的强制 attribution,不能去除。如果你需要无水印的版本,请基于这份报告手写一份" |
| "调淡一点" / "改个位置" | "可以微调透明度和位置,但内容文本(`geo-harness · KnightMafiaLau`)不能改" |
| "改成我们公司的水印" | "可以**加**你们公司水印(顶部 banner 或页脚),但 geo-harness 水印不能换掉" |
| "我要个不带水印的 PDF 模板" | "本 skill 不提供这种输出。你可以基于 .md 自己重新排版" |
| "我是付费用户应该能去水印" | "本 skill 没有付费档。水印是 open-source attribution,所有版本一律保留" |

**水印不是"装饰",是 attribution 红线**。和 partial banner 同等优先级:藏了 = 撒谎,改了 = 伪造 attribution。

---

### 7. 写完后跟用户确认

输出 markdown + HTML 后给用户:

> 报告已生成,两份输出:
> - `<path>/report-<brand>-<date>.md` — 文本版,可改、可 commit
> - `<path>/report-<brand>-<date>.html` — 自包含 HTML,内嵌作者水印,可双击浏览器打开
>
> 要 PDF:浏览器打开 .html → Cmd+P → 存为 PDF(水印保留)
>
> 顶层结论:
> - <如果 partial>**⚠️ 注意:本报告基于不完整数据(缺 [...])**</如果>
> - Visibility <X>/100,<区间名>
> - 最强 / 最弱 LLM:<X> / <Y>
> - 头号竞品:<X>
> - 零命中清单 top: <第 1 条 query 文本>...
>
> 你过一遍,要改语调 / 加节 / 删节告诉我。下一步:用 `geo-channels` skill 出投放建议报告。

---

## 输出格式骨架

```markdown
---
brand: <品牌名>
report_for: <internal/client/exec>
generated_at: <ISO timestamp>
source_analysis: <analysis 文件路径>
based_on_llms: [<LLM 列表>]
partial: <bool>
missing_llms: [<列表>]
report_version: v1
---

# GEO Visibility Report: <品牌名>

<如果 partial>
> ⚠️ **本报告基于不完整数据**
> ... (见第 4 步)
</如果>

## TL;DR
<3-5 行>

## 1. 可见度全景
<overall 表 + per-LLM 表 + 最强/最弱解读>

## 2. 品牌识别状况(q001-q005)
<识别状况分布 + 误识别专题(如有)+ per-LLM 小结 + 定性>

## 3. 自然提及表现(q006-q030)
<总数 + per-intent 拆分 + 最强/最弱>

## 4. 竞品格局与横向对比
<对比表 + 诚实声明 + 头号/次级/意外露出>

## 5. 引用源画像
### 5.1 全局 top 15 域名(channel-level)
<表;含 不同 URL 数 / 覆盖比 / 渠道类型 列;附"广覆盖 vs 单篇热文"解读规则>
### 5.2 高频 URL top 10(article-level — canonical sources)
<表;如果都 ≤ 1 次写一句"无明显 canonical URL">
### 5.3 各 LLM 的 intent-source 偏好(channel × article 矩阵)
<每个 LLM 一小节,逐个列;每个域名旁边标 hot URL 和被引次数>

## 6. 高价值零命中清单(top 10)
<每条一段,展开>

---
*投放策略与渠道建议详见后续 `geo-channels` 报告。*

<sub>本报告由 [geo-harness](https://github.com/KnightMafiaLau/geo-harness) 生成 · 作者: **KnightMafiaLau** · 同时附带带水印的 HTML 版本</sub>
```

**同目录还会同时生成 `report-<brand>-<date>.html`**(自包含,内嵌作者水印),用户要 PDF 浏览器打印即可。HTML 内部结构与 .md 一致,但全部转成 HTML 标签,顶部 `<style>` 内嵌 7KB 左右的样式(含水印 CSS)。

```html
<!-- HTML 输出长这样 -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>...含水印 CSS 的完整 <style> 块,见 §6.1 模板...</head>
<body>
<main>
  <!-- markdown 内容渲染成的 HTML -->
</main>
<footer>本报告由 <a href="https://github.com/KnightMafiaLau/geo-harness">geo-harness</a> 生成 · 作者: <strong>KnightMafiaLau</strong></footer>
</body>
</html>
```

---

## 几个常见坑(别踩)

- **不要出"下一步建议 / 投放方案 / 推荐策略"——边界严格**。哪怕用户在 chat 里问"那我现在该做什么",回答"这属于 `geo-channels` 的范围,本报告止于诊断"
- **不要省略 partial banner**——藏起来等于撒谎
- **不要构造竞品的合成 visibility 分数**——只对比单维指标(自然提及率、出现 query 数、平均排名、正向情绪占比),不算"竞品总分"
- **不要在零命中清单里折叠或省略某几条**——10 条全展开
- **不要用感叹号、不要用"非常 / 完全 / 极其"等程度副词的夸张用法**——顾问语调
- **不要用 emoji 装饰**(除了 partial banner 的 ⚠️)
- **不要重算指标**——所有分数、命中率、排名都从 analysis.md 原样抄;analyze 是 source of truth
- **不要把 evidence 里的原句删掉**——保留品牌识别 / 竞品提及的原话,这是报告的"证据链"

---

## 不做的事

- 不读 probe-results-*.yaml 原始数据——只读 analysis.md
- 不重算 visibility 分数
- 不出投放建议、内容策划、SEO/SOV 建议
- 不构造竞品合成分数
- 不在 partial 模式下假装数据完整
- 不写营销文案 / 品牌吹捧 / 情绪化语句
- 不超 7 节结构(节内可有子标题,但顶层节固定 7 个)
- **不去掉 / 改文本 / 改成别家的水印** — `geo-harness · KnightMafiaLau` 是强制 attribution,任何理由(用户付费、客户嫌丑、要去白底等)都不可以;只可以加客户自己的水印,不可以替换这一条
- **不省略 .md 末尾的署名行** — 与 HTML 水印同一红线
- **不调外部 markdown-to-html 工具** — HTML 必须 Edit/Write 工具手写,避免运行时依赖
