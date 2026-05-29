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

### 1. 拿 2 项输入

1. **probe-results 文件路径**（1 个或多个）。常见形态：
   - 单 LLM：`./probe-results-kimi-2026-05-30.yaml`
   - 多 LLM：用户给一个目录，或者列出多份
2. **输出路径**——默认 `./analysis-<brand>-<date>.md`，用户可改

### 2. 读所有输入文件 + 校验

每份文件都用 `Read` 工具读进来。读完做基本校验：

- ✓ 必须有 `brand` / `target_llm` / `results` 字段
- ✓ 所有文件的 `brand` 必须一致（否则停下问用户："你给了不同品牌的 probe 结果，是想合一起还是分开分析？")
- ✓ 每条 result 必须有 `query_id` / `intent` / `status`
- ✓ status=success 的至少要有 `summary.target_brand`（schema 不对就停，让用户检查）

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

跨所有 query 所有 LLM，统计 `citations` 列表里每个域名：

- `appearances`：总出现次数
- `appearing_in_intents`：在哪些 intent 类型里出现过（去重）
- `appearing_in_llms`：在哪些 LLM 上被引用过（去重）

按 `appearances` 降序排，取 **top 15**。

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

## 引用源域名 Top 15

| 域名 | 出现次数 | 主要 intent | 出现 LLM |
|---|---|---|---|
| 36kr.com | 18 | 探索发现 / 选型推荐 | Kimi, 豆包 |
| zhihu.com | 12 | 选型推荐 | Kimi, DeepSeek |
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
- 不要把 probe 阶段已经判断好的字段（mentions / sentiment / rank）**重判**——口径不一致会越改越乱
