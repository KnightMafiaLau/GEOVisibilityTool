---
name: geo-analyze
description: 给一份或多份 probe-results-*.yaml（geo-probe 的输出），算出 visibility 分数、识别率、自然提及率、平均排名、竞品分布、引用源画像、高价值零命中清单。输出 analysis.md（供下一步 geo-report 消费）。纯 skill，不带 Python：数据量小、判断活多。
triggers:
  - 分析 probe 结果
  - 算 GEO 分数
  - 算可见度分数
  - 跑 visibility
  - 出零命中清单
  - geo-analyze
metadata:
  author: KnightMafiaLau
  source: geo-harness v0.1
user-invocable: true
disable-model-invocation: false
---

# geo-analyze — 把 probe 数据算成 visibility 报告输入

## 什么时候用

用户跑完 `geo-probe`，拿到了 1 个或多个 `probe-results-<llm>-<date>.yaml`，想算出：
- 总 visibility 分数（每个 LLM + 跨 LLM）
- 识别率 / 自然提及率 / 平均排名 / 推荐率 / 情绪
- 竞品分布（谁在替你占位）
- 引用源 top 域名（该往哪发内容的线索）
- **高价值零命中清单**（该出现但没出现的关键 query）

**这个 skill 只算 + 落数据。不出最终对外报告——那是 `geo-report` 的事。**

## 你（Claude）要做的事

### 1. 定位"测试目录" + 读 probe-plan.yaml 对账（**关键防漏步**）

#### 1.1 定位测试目录

用户调用本 skill 时通常只丢一个东西过来:

- 一个目录（最常见）
- 或一份 probe-results-*.yaml 文件路径（从中推出父目录）
- 或一份 probe-plan.yaml 路径（从中推出父目录）

**所有相关文件假设在同一目录**（geo-probe 已经强制了这一点）。先把"测试目录"算出来,后面 plan / 所有 probe-results / 输出 md 都在这个目录下。

#### 1.2 读 probe-plan.yaml

在测试目录下找 `probe-plan.yaml`。

**情况 A — plan 存在(标准路径)**:

读出 `planned_llms` 和 `completed`,算 `pending = planned_llms - [c.llm for c in completed]`。

**情况 A.1 — pending 为空(全跑完了)**:
- 按 plan.completed 列表拿到所有 probe-results 文件路径
- 报一句"plan 显示 N 个 LLM 全部跑完,开始分析" → 继续后面流程

**情况 A.2 — pending 非空(有缺口) → STOP,停下来跟用户对话**:

这是核心防漏点。**不要列 a/b/c 菜单,直接对话式跟用户对账**:

> 我在测试目录看到 `probe-plan.yaml`:
> - 你计划测 **N** 个 LLM: [planned 列表]
> - 已完成 **M** 个: [completed 列表]
> - **还差 K 个没跑**: [pending 列表]
>
> 我先停一下——这几个没跑完,直接 analyze 会拿到 partial 数据,visibility 分数和零命中清单都会有偏差。
>
> 你想怎么处理?
> - 我现在回去帮你把缺的跑了(推荐;直接告诉我先跑哪个,我接着调 geo-probe)
> - 改 plan,把缺的从 planned_llms 里删掉(明确放弃测这几个就不算缺口了)
> - 强制用现有 M 份做 partial 分析(我会在输出 md 里把 `partial: true / missing: [...]` 标得醒目,提醒下游 geo-report 这是不完整数据)

**等用户明确回复再继续**。**不要自作主张挑路**。

**情况 B — plan 不存在(用户跳过了 plan 机制 / 旧数据)**:

降级到 sniff 模式:

1. glob 测试目录下所有 `probe-results-*.yaml`
2. 读每份的 header,拿 `target_llm` 名,列给用户:
   > 没找到 probe-plan.yaml。我在目录里 sniff 到 N 份 probe-results:
   > - probe-results-kimi-2026-05-30.yaml (LLM: Kimi)
   > - probe-results-doubao-2026-05-30.yaml (LLM: 豆包)
   > ...
   > 用这 N 份分析吗?如果原计划还有别的 LLM 没跑,现在告诉我,我先去补。

等用户明确点头再继续。**不要静默继续**——这是当时 bambulab 案例漏 qwen 的直接原因。

#### 1.3 输出路径

默认 `<测试目录>/analysis-<brand>-<date>.md`,用户可改。

### 2. 读所有 probe-results 文件 + 校验

按上一步确定的文件列表,每份用 `Read` 工具读进来。读完做基本校验：

- ✓ 必须有 `brand` / `target_llm` / `results` 字段
- ✓ 所有文件的 `brand` 必须一致（否则停下问用户："你给了不同品牌的 probe 结果，是想合一起还是分开分析？")
- ✓ 每条 result 必须有 `query_id` / `intent` / `status`
- ✓ status=success 的至少要有 `summary.target_brand`（schema 不对就停，让用户检查）

**读完汇报一次**(再次防漏):

> 已加载 **N** 份 probe-results,覆盖 LLM: [list]。每份 results 条数: [Kimi=30, 豆包=30, ...]。开始算分析?

### 3. 按下面口径算 6 个核心指标

#### 口径一：识别率 (recognition_rate)

只看 **q001-q005**（intent = 品牌识别）：

```
识别率 = ( target_brand.mentions > 0 且 sentiment ≠ negative 的条数 ) / 5
```

注意：
- sentiment = negative 通常意味着"误识别"——名字识别到了但串到了别家。**不算正确识别**。
- status = error 的不计入分母（只算 success 的 5 条；如果 5 条全 error，识别率标记为 `N/A`）

#### 口径二：自然提及率 (mention_rate)

只看 **q006-q030**（intent ≠ 品牌识别）：

```
自然提及率 = ( target_brand.mentions > 0 的条数 ) / 25
```

注意：
- 不管 sentiment 怎样、不管 rank 多少，**字面出现 ≥1 次就算命中**。这一项测的是"模型有没有自然想到你"。
- 描述性提及（在 notes 里的）**不算**，因为 mentions 字段定义就是字面计数。
- status = error 的不计入分母。

#### 口径三：平均排名 (avg_rank)

只看 `target_brand.rank ≠ null` 的条目（必然在对比/推荐类 intent 里）：

```
平均排名 = sum(rank) / count(rank ≠ null)
```

注意：
- 如果一次都没被排进任何榜单 → `avg_rank: null`，**不要补 0 也不要补 999**。null 就是 null，下游 geo-report 需要这个信号。

#### 口径四：推荐率 (recommended_rate)

只看 `recommended ≠ null` 的条目（必然在推荐/选型类 intent 里）：

```
推荐率 = count(recommended == true) / count(recommended ≠ null)
```

如果分母为 0（这份 probe 里没有任何推荐类 query） → `recommended_rate: null`

#### 口径五：正向情绪率 (positive_sentiment_rate)

只看 `mentions > 0` 的条目（即被实际提到的次数）：

```
正向情绪率 = count(sentiment == positive) / count(mentions > 0)
```

如果分母为 0（完全没命中） → `positive_sentiment_rate: null`

#### 口径六：visibility_score（0-100，加权合成）

```
visibility_score =
    自然提及率   * 40
  + 识别率       * 30
  + 排名分       * 20
  + 正向情绪率   * 10
```

其中 **排名分** 定义为：

```
if avg_rank == null:
    排名分 = 0      （从没被排过，给 0；这与"被排过但很差"区分开）
else:
    排名分 = max(0, 1 - (avg_rank - 1) / 9)   # rank=1 → 1.0；rank=10 → 0.0
```

**指标为 null 时怎么算分**：
- 识别率 N/A → 把识别率分量从公式里**去掉**，并按剩下权重重新归一化（总分仍是 0-100）。同理推荐率/情绪率。
- 这是为了别让"用户没跑品牌识别类"这种数据缺失把分数搞崩。在输出里**必须写明哪些分量被去掉了**，便于 geo-report 解释。

### 4. 按 LLM 分别算，再算 overall

对**每个 LLM**（每份 probe-results 文件）独立跑一次第 3 步 → 得到 `per_llm` 区块。

`overall` 区块 = 把每个 LLM 的指标做**算术平均**。不要按 LLM 用户量加权——拍权重不客观。

如果只测了 1 个 LLM：
- per_llm 还是写
- overall 直接等同于该 LLM 的分数（**别省略 overall 区块**，下游 geo-report 默认读 overall）

### 5. 算竞品分布

跨所有 LLM 所有 query，聚合 `summary.other_brands`：

对每个出现过的品牌名（**做合并**：如"智元"和"智元机器人"算一个，你自己识别简写），统计：

- `mentions_total`：所有 `mentions` 数值之和
- `queries_appeared`：在多少条独立 query 里出现过（同 query 同 LLM 算 1 次；同 query 跨 LLM 各算 1 次）
- `avg_rank`：所有非 null `rank` 的算术平均（null 不计入）
- `top_llm`：在哪个 LLM 上 `mentions_total` 最高
- `sentiment_mix`：positive/neutral/negative 各多少次

按 `mentions_total` 降序排，取 **top 10**。

### 6. 算引用源域名 top（这是 geo-channels 的关键输入）

**⚠️ 重要 schema 变更**(2026-05-30):`citations` 字段现在存的是 **URL 列表**(不去重),不再是域名列表。同一域名多个 URL 全保留——频次本身是"该渠道权重"的信号。

提取域名要在 analyze 阶段**现算**:对每条 URL `urlparse(url).netloc.lower()`,得到 hostname。

跨所有 query 所有 LLM,统计每个**域名**(从 URL hostname 派生):

- `appearances`:URL 出现的总次数(**同域名多个 URL 都计数;同 URL 多次出现也计数**——这就是"该渠道值得多投放"的根据)
- `unique_urls`:该域名下出现过多少个**不同** URL(衡量"覆盖广度":1 个 URL 引 10 次 vs 10 个 URL 各引 1 次,后者更强)
- `appearing_in_intents`:在哪些 intent 类型里出现过(去重)
- `appearing_in_llms`:在哪些 LLM 上被引用过(去重)

按 `appearances` 降序排,取 **top 15**。**报告这张表时同时显示 `unique_urls`**,这是区分"一篇热文反复被引"和"该站多篇内容都被引"的关键。

**向后兼容**:如果遇到旧 schema 的 probe-results(`citations` 直接是域名列表,不是 URL),把每个域名当一个 URL 处理(`urlparse('domain.com').netloc` 返回空,所以这种情况下直接拿字符串当 hostname)。在 analysis.md frontmatter 里标 `legacy_citations_schema: true` 警示下游。

### 6.5 算 per LLM × per intent 引用源偏好矩阵(geo-report 节 6.2 的输入)

除了上面的全局 top 15,还要算一份**细粒度的引用源偏好矩阵**——这是 `geo-report` 用来诊断"模型在某类问题上偏好引哪些站"的关键数据。

对每个 LLM × 每个 intent 类型(6 类),统计:

- 该 (LLM, intent) 组合下出现过的所有域名(从 URL 现算 `urlparse(url).netloc`)
- 每个域名在该组合下的**出现次数**(URL 级,不去重)
- 取 top 5(不足 5 个就有几个列几个;少于 3 个的标记"数据稀疏")

输出形式(在 analysis.md 里用嵌套小节呈现,见输出格式)。

**数据稀疏阈值**:某 (LLM, intent) 组合下:
- 总 citation 数 < 3 → 标 `sparse: true`,不列具体域名(避免被读者误读为"偏好")
- 总 citation 数 ≥ 3 → 正常列 top N

**没出现的组合也要记**(标 `no_data` 而非省略),否则 geo-report 不知道是"真的没数据"还是"analyze 漏算了"。

### 7. 挑高价值零命中（**这是判断活，重点**）

不是所有 0 提及都算"高价值零命中"。按以下规则筛：

**必须满足**：
- intent ∈ {`选型推荐`, `对比评估`, `采购/投资`}（商业意图明确）
- 至少 1 个 LLM 上 `target_brand.mentions == 0`
- 该 query 在那个 LLM 上**至少有 1 个竞品出现**（说明位置存在，只是你没占）

**排除**：
- intent = `了解原理`（普及性问题，品牌出现本就少）
- intent = `探索发现` 中**没有竞品出现**的（说明模型在该问题上根本不点名公司）

**排序**：按"该 query 上竞品总出现数"降序（出现越多 = 该位置越值钱 = 你越亏）

**取 top 10**，每条给出：
- `query_id` / `intent` / `text`
- `competitors_that_appeared`（在该 query 上出现的竞品名 + 该 LLM）
- `missed_in_llms`（在哪几个 LLM 上 0 命中）
- `why_high_value`（一句话，**Claude 写**，例："直接选型意图，3 家竞品在 Kimi 上被点名推荐，我们完全缺席"）

### 8. 算品牌识别细节（q001-q005 的逐条状态）

这是 0 收录 / 误识别信号的核心。对每个 LLM 的 q001-q005，逐条记录：

- `query_id` / `text`
- `mentions` / `sentiment` / `rank` / `recommended`
- `notes`（原样抄过来 probe 阶段写的 notes，比如"误识别为某教育公司"）
- `status_label`：你来归类，三选一：
  - `recognized`（正确识别）
  - `not_recognized`（明确说不知道）
  - `misidentified`（串到了同名/类似的别家）

### 9. 输出 markdown

落到 `analysis-<brand>-<date>.md`，结构按下面【输出格式】。

**重要**：这份 md 是给下一步 `geo-report`（也是 AI）读的，所以：
- 字段用 markdown 表格 + 标题层级清晰
- 数值都列出来，**不要省略**
- 关键发现用 **加粗** 标出（便于 geo-report 抓重点）
- 但**不要写"建议"或"行动方案"**——那是 geo-report 的活

### 10. 输出后跟用户确认

> 分析完成。
> - 输出文件：<路径>
> - 跨 LLM 总分：**<X> / 100**（<识别率/自然提及率/平均排名> 三个核心数）
> - 最强 / 最弱 LLM：<X> / <Y>
> - 主要威胁竞品：<前 3 个>
> - 高价值零命中：<N> 条
>
> 下一步：用 `geo-report` skill 出对外报告。

---

## 输出格式（analysis-<brand>-<date>.md）

```markdown
---
brand: <品牌名>
analyzed_at: <ISO timestamp>
llms_analyzed: [<LLM1>, <LLM2>, ...]
queries_total: 30
analysis_version: v1
partial: false                       # 只有用户明确选择"用现有的跑 partial"才设 true
missing_llms: []                     # 当 partial: true 时,列出计划但缺数据的 LLM
---

# GEO Analysis: <品牌名>

## Overall（跨 LLM 平均）

- **Visibility Score: <X> / 100**
- 识别率: <X>% (<n>/5 平均)
- 自然提及率: <X>% (<n>/25 平均)
- 平均排名: <X> 或 null
- 推荐率: <X>% 或 null
- 正向情绪率: <X>% 或 null
- 排除分量: [<被去掉的指标列表，如果有>]

## Per-LLM

### <LLM 名>
- Visibility Score: <X> / 100
- 识别率: <X>% (<n>/5)
- 自然提及率: <X>% (<n>/25)
- 平均排名: <X> 或 null
- 推荐率: <X>% 或 null
- 正向情绪率: <X>% 或 null
- 排除分量: [...]

（每个 LLM 一段）

## 品牌识别细节 (q001-q005)

| LLM | query_id | mentions | sentiment | status_label | notes 摘要 |
|---|---|---|---|---|---|
| Kimi | q001 | 0 | null | not_recognized | LLM 明确说不知道 |
| Kimi | q002 | 2 | negative | misidentified | 串到同名教育公司 |
| ...

## 竞品分布（top 10，按总提及次数降序）

| 品牌 | 总提及 | 出现 query 数 | 平均排名 | 最强 LLM | 情绪(+/0/-) |
|---|---|---|---|---|---|
| 智元 | 47 | 22 | 1.3 | Kimi | 30/15/2 |
| 宇树 | 31 | 18 | 2.1 | 豆包 | 20/10/1 |
| ...

## 引用源域名 Top 15(全局)

| 域名 | 出现次数 | 主要 intent | 出现 LLM |
|---|---|---|---|
| 36kr.com | 18 | 探索发现 / 选型推荐 | Kimi, 豆包 |
| zhihu.com | 12 | 选型推荐 | Kimi, DeepSeek |

## 引用源 per LLM × per intent 偏好矩阵

按 LLM 分小节,每个小节列该 LLM 在 6 类 intent 下的 top 5 域名:

### Kimi
- **品牌识别**: zhihu.com (3) / weibo.com (2) — *sparse: false*
- **探索发现**: 36kr.com (8) / zhihu.com (5) / sohu.com (3) — *sparse: false*
- **选型推荐**: zhihu.com (10) / bilibili.com (6) / chiphell.com (4) — *sparse: false*
- **对比评估**: bilibili.com (5) / b23.tv (3) — *sparse: false*
- **了解原理**: csdn.net (2) — *sparse: true*  ← 少于 3 条,标 sparse
- **采购/投资**: *no_data*  ← 该 LLM 在该 intent 类下完全没引用任何源

### 豆包
(同样格式,逐个 LLM 写)
| ...

## 高价值零命中清单（top 10）

### 1. q012 (选型推荐)

- **原问题**：做 RAG 知识库项目，初创团队选哪个向量库最省心？
- **竞品占位**：智元(Kimi rank 1) / 宇树(Kimi rank 2) / 优必选(豆包 rank 1)
- **完全缺席的 LLM**：Kimi / 豆包 / DeepSeek
- **为什么高价值**：直接选型意图，3 家竞品在两个主流 LLM 上被点名推荐，我们 0 命中

### 2. ...

（每条一段）

## 数据完整性

- probe-results 文件读取：<N> 份
- 总 results 条数：<N>
- success：<N> / error：<N>
- 被丢弃的条目：<N>（说明原因）
```

---

## 几个常见坑（别踩）

- **不要把"描述性提及"加到 mentions 计数**——probe 阶段已经明确分开了，notes 里的描述性提及只是定性信号，不进算式
- **avg_rank = null 不要补数**——null 是关键信号（"从未被排过"），下游需要区分"被排过但很差"和"从来没上过榜"
- **指标缺失要归一化重算，不要补 0**——参考第 3 步口径六的说明
- **竞品合并要谨慎**——"智元" / "智元机器人" / "AgiBot" 是同一家就合并；不确定就分开列，让用户后续告诉你
- **零命中筛选别"全 0 提及条数"**——那个数没意义。要按"商业意图 + 竞品占位"过滤
- **不要算"竞品 visibility 分数"**——这是 `geo-report` 的事，超出了 analyze 的范围
- **不要写建议 / 行动方案 / 推荐**——分析归分析，建议归 `geo-report`

---

## 不做的事

- 不要发起新 probe（不会去问 LLM）
- 不要修改 probe-results 文件（只读）
- 不要写"对外报告"风格的措辞（"我们建议..."）——这是 geo-report 的事
- 不要算"竞品的可见度分数"
- 不要拍 LLM 用户量权重——跨 LLM 一律算术平均
- 不要假装数据齐全——缺失就标 null，并在输出里写清楚为什么
- **不要静默继续**——如果 probe-plan.yaml 显示 pending 非空,或 sniff 出与预期不符的文件数,**必须停下来对话**,不要悄悄按"有什么用什么"算分
- **partial: true 是用户明确决策才设的**——不准默认 true,不准为了"能跑就跑"自动降级
- 不要把 probe 阶段已经判断好的字段（mentions / sentiment / rank）**重判**——口径不一致会越改越乱
