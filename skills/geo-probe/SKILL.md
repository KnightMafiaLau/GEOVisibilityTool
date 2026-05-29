---
name: geo-probe
description: 给一份 queries.yaml（geo-queries 生成的）和一个目标 LLM（内置 6 个预设：Kimi / 豆包 / DeepSeek / 百度文心 / 千问 / 元宝；也支持用户自定义任何 LLM），逐条把问题问到目标 LLM 的网页端，记下每条的：完整回答、命中的品牌（你的 + 竞品）、引用的源（URL + 域名 + 标题）。输出 probe-results.yaml。每次只跑一个 LLM。Skill 配套 probe.py（仅 stdlib，机械活专用）。
triggers:
  - 探测 LLM
  - 跑 GEO 测试
  - 用问题清单去问 LLM
  - 把问题问到 Kimi/豆包/DeepSeek
  - probe LLM
metadata:
  author: KnightMafiaLau
  source: geo-harness v0.1
user-invocable: true
disable-model-invocation: false
---

# geo-probe — 把测试问题问到真实 LLM

## 什么时候用

用户拿到了一份 GEO 测试问题清单（通常是 `geo-queries` 生成的 `queries.yaml`），想拿这些问题去真实 LLM 上问一遍，记下每个 LLM 怎么回答、提到了哪些品牌、引用了哪些源。

**这个 skill 只负责"问 + 记"。不算分、不出报告、不做对比——那是后续模块的事。**
**每次只跑一个 LLM**。要测多个 LLM，就把这个 skill 调用多次。
**配套 `probe.py` 做机械活**（定时、文件追加、URL 抽取），仅 stdlib，无需 install。

## 你（Claude）要做的事

### 1. 先拿到 5 项输入

1. **queries.yaml**（路径或粘贴内容）——schema 要符合 geo-queries 的输出
2. **目标 LLM**——下面两种之一：

   **预设**（用户报名字即可）：
   - `Kimi` → https://www.kimi.com
   - `豆包` → https://www.doubao.com
   - `DeepSeek` → https://chat.deepseek.com
   - `百度文心` → https://yiyan.baidu.com
   - `千问` → https://chat.qwen.ai
   - `元宝` → https://yuanbao.tencent.com

   **自定义**（用户给三项）：
   - `name`：报告里显示用（如 "Gemini"、"ChatGPT"、"内部 LLM"）
   - `url`：聊天界面入口
   - `notes`（可选）：登录要求、特殊操作、网页结构提示

3. **输出路径**——默认 `./probe-results-<llm>-<date>.yaml`，用户可以改
4. **你（agent）有没有浏览器工具**——没有就停下来告诉用户："这个 skill 需要 agent 有浏览器能力（Claude-in-Chrome / Codex 浏览器 / 别的 MCP），装上再调"
5. **延迟范围**（可选）——默认 `--min 20 --max 60` 秒之间随机。想更保险（不易触发风控）就调大，想更快就调小。**不允许设成 0 或 < 5 秒**——会被风控当爬虫。

### 2. 开跑前必须先确认

把信息总结给用户，明确请求授权：

> 准备探测 **<品牌名>** 在 **<LLM>** 上的可见度：
> - 共 30 条问题
> - 估计 15-30 分钟（含 20-60 秒随机间隔）
> - 我会用 [浏览器工具名] 一条一条问，全程不打断
> - 输出文件：<路径>
>
> 确认开跑吗？（y/n）

用户没明确说 "y" / "好" / "开跑" 之前**绝对不要开始**。

### 3. 用第 1 条做"探路"

不要直接 30 条全跑。先做这些：

1. 用户授权后，先初始化输出文件：
   ```
   python3 probe.py init <output-path> \
     --brand "<品牌名>" --llm "<LLM 名>" --total 30 \
     --probed-at "<ISO 时间戳>" --probed-by "<浏览器工具名>"
   ```
2. 打开目标 LLM 的网址
3. 如果需要登录 / 撞验证码 / 网页结构变了 → **停下来报给用户**，让他处理后再继续
4. 问 q001，等回答完整出现
5. 抓回答全文，做以下事：
   - 语义判断命中了哪些品牌（见第 4 步规则）
   - `echo "<answer-text>" | python3 probe.py extract-citations` → 拿到 citations YAML 块
   - 组装一条 result block（见输出 schema），通过管道追加：`echo "<block>" | python3 probe.py append <output-path>`
6. 让用户瞄一眼："第 1 条跑通了，回答约 N 字，命中了 [品牌1, 品牌2]，引用了 [N] 个源。继续跑剩下 29 条吗？"

用户点头后再继续。

### 4. 跑剩下的 29 条

对每条 query：

1. **开新对话**（不要在一个对话里串着问 30 条——会污染上下文，破坏"真实用户单次提问"的测试条件）
2. 把 `query.text` 原样发过去
3. 等回答完整出现
4. **抓回答**：记下字符总数 `answer_chars`，但**不存全文**（省 token；如需复核就重跑）
5. **生成结构化 summary**（这是这条 result 的核心）：

   **gist**（80-120 字）—— 概括 LLM 说了什么。例："列了 5 家国内向量数据库公司，按团队规模排序，重点推荐 Milvus，次推 Qdrant，简述各自定位与适用场景。"

   **target_brand**（用户品牌，即使 0 提及也要填字段，全 null）：
   - `mentions`: **字面**出现次数（描述性提及不算 mentions，单独放 notes）
   - `sentiment`: positive / neutral / negative / null
     - positive: 被推荐、列为代表玩家、点名优势、进 top N
     - neutral: 只是被罗列，没褒贬
     - negative: 被指缺点、被排除、对比时落下风
     - null: 没提到
   - `rank`: 对比/推荐类里排第几（1-N）；不适用或没出现就 null
   - `recommended`: true / false / null
     - true: 推荐/选型类里被明确推荐
     - false: 推荐类里被明确排除或缺席
     - null: 不是推荐类问题
   - `evidence`: 数组，**抄下所有提到目标品牌的原句**（用户要求保留）

   **other_brands**（其他被提到的品牌，不分竞品/非竞品）—— 每个一项，字段同上但**不含 evidence**

   品牌识别规则：
   - 目标品牌 + 常见简写/别名（你自己识别，比如"桥介数物"→"桥介"）
   - 别名的字面出现也计入 mentions

6. **抽引用域名**：`echo "<answer>" | python3 probe.py extract-citations` → 拿到去重的 domain 列表
7. **品牌识别类（`intent: 品牌识别`）的特殊处理**：
   - LLM 完全没识别（说"不知道"）→ `target_brand` 全 null，notes 写"0 收录"
   - LLM 把品牌**串到另一家同名公司**了 → notes 写明"误识别"（**关键 GEO 信号**），`target_brand.mentions` 仍记字面次数但 sentiment 标 negative
   - LLM 识别正确 → 正常记
8. **描述性提及单独记 notes**（不进 mentions 计数）：如 LLM 说"一家做具身智能小脑的初创"且画像吻合用户品牌，在 notes 里写"描述性提及：'...原句...'"
9. **追加结果**：组装 result block → `echo "<block>" | python3 probe.py append <output>`（每条立刻持久化）
10. **等下一条**：`python3 probe.py wait --min <X> --max <Y>`（默认 20 / 60；这是 Python `time.sleep`，硬执行）

### 5. 失败处理：停下来问用户

任何一条 query 跑不下去，停止 probe，把现状告诉用户，让用户决定下一步：

触发情况：
- 网页报错 / 请求超时 / 撞验证码
- LLM 超过 2 分钟没回答
- 浏览器工具自己出错
- 任何你不确定该怎么处理的情况

报话术：

> 跑到 **q017** 的时候出问题了：[具体什么问题]
> 已经跑完的 N 条结果已经保存到 [文件路径]（每条都是即时存盘的，不丢）。
> 你想怎么处理？
> - 跳过这条继续往下跑
> - 重试这条
> - 整个 probe 在这停掉

**不要自作主张跳过。不要硬撑。不要编答案。**

### 6. 输出格式（`probe.py` 维护，你只需理解 schema）

```yaml
brand: <品牌名>
target_llm: <LLM 名，可以是预设也可以是自定义的 name>
probed_at: <ISO timestamp>
probed_by: <agent 用的浏览器工具名>
queries_total: 30

results:
  - query_id: q001
    intent: 探索发现
    text: <原问题>
    status: success
    answer_chars: 1247               # 只记长度，不存全文

    summary:
      gist: |
        <80-120 字概括 LLM 说了什么>
      target_brand:
        mentions: 1                  # 字面出现次数
        sentiment: positive          # positive / neutral / negative / null
        rank: 3                      # 对比/推荐类的排名；不适用就 null
        recommended: true            # true / false / null
        evidence:                    # 抄下所有提到目标品牌的原句
          - "桥介数物是一家专注具身智能小脑的初创公司..."
      other_brands:
        - name: 智元
          mentions: 3
          sentiment: positive
          rank: 1
          recommended: true
        - name: 宇树
          mentions: 2
          sentiment: positive
          rank: 2
          recommended: true

    citations:                       # 去重的域名列表
      - 36kr.com
      - zhihu.com

    notes: null                      # 描述性提及 / 误识别 / 其他特殊情况

  - query_id: q017   # 失败的 query 也要记
    intent: 选型推荐
    text: <原问题>
    status: error
    error_message: <具体什么错>
    summary: null
    citations: []
```

### 7. 跑完总结

读一遍输出文件，给用户：

> Probe 完成。
> - 输出文件：<路径>
> - 成功 <N> / 失败 <M>
> - 目标品牌 **<品牌名>** 命中 <X> 条（<X/N> %）
> - 出现最多的竞品：<前 3 个>
> - 引用源最常见的域名：<前 5 个>
>
> 下一步：用 `geo-analyze` skill 把这份结果算成 visibility 分数和报告。

---

## Python 辅助命令（`probe.py`）

仅 stdlib，无需 install。所有机械活都在这里。

```
python3 probe.py wait [--min 20] [--max 60]
  随机等 min ~ max 秒（防风控）。

python3 probe.py init <path> --brand <X> --llm <Y> --total <n> \
                   --probed-at <ts> --probed-by <tool> [--overwrite]
  创建输出文件，写头部。

python3 probe.py append <path>
  从 stdin 读 YAML 块（必须以 "- " 开头）原子追加到 <path>。

python3 probe.py extract-citations
  从 stdin 读文本，抽出 URL 并提取域名，输出去重排序的域名 YAML 列表。
```

---

## Few-shot：输出长这样（节选）

假设跑 桥介数物 in Kimi：

```yaml
brand: 桥介数物
target_llm: Kimi
probed_at: 2026-05-30T10:23:00Z
probed_by: Claude-in-Chrome
queries_total: 30

results:
  - query_id: q001
    intent: 探索发现
    text: 国内做具身智能小脑的公司有哪些值得关注？
    status: success
    answer_chars: 842
    summary:
      gist: |
        列了 4 家国内具身智能小脑方向值得关注的公司，按知名度排序，
        头部点名智元和宇树，简述各自团队背景与技术路线，
        中间提到星动纪元，未提及桥介数物。
      target_brand:
        mentions: 0
        sentiment: null
        rank: null
        recommended: null
        evidence: []
      other_brands:
        - name: 智元
          mentions: 3
          sentiment: positive
          rank: 1
          recommended: true
        - name: 宇树
          mentions: 2
          sentiment: positive
          rank: 2
          recommended: true
        - name: 星动纪元
          mentions: 1
          sentiment: neutral
          rank: 3
          recommended: null
    citations:
      - 36kr.com
      - zhihu.com
    notes: |
      描述性提及：回答提到"一些专注小脑控制器的初创团队"，画像吻合桥介数物
      但未点名，不计入 mentions。

  - query_id: q026   # 品牌识别类
    intent: 品牌识别
    text: 桥介数物是一家什么公司？
    status: success
    answer_chars: 78
    summary:
      gist: |
        LLM 表示未找到"桥介数物"这家公司的可靠信息，
        未给出任何描述或推测，未提及其他公司。
      target_brand:
        mentions: 0
        sentiment: null
        rank: null
        recommended: null
        evidence: []
      other_brands: []
    citations: []
    notes: |
      LLM 完全没识别到品牌——0 收录。
      这是 GEO 的关键信号：目标品牌在 Kimi 上不被识别。
```

---

## 不做的事

- 不要在没确认前开跑
- 不要在浏览器工具失效 / 撞验证码时硬撑或编造答案
- 不要在一个对话里串问多条（会污染上下文）
- 不要算分、出报告、做品牌对比——那是 `geo-analyze` / `geo-report` 的事
- 不要并行跑多个 LLM——一次跑一个，要测多个就调多次
- 不要存全文（schema 改了，只存 `answer_chars` + summary；想复核就重跑）
- 不要把描述性提及计入 mentions（mentions 只算字面出现，描述性提及进 notes）
- **不要绕开 `probe.py wait`**——不要把 `--min --max` 都改成 0 或 < 5
- **不要自己手写 YAML 追加**——必须走 `probe.py append`（防止格式坏掉）
