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

### 1. 先拿到输入 + 处理 probe-plan.yaml（**关键：每个测试 run 的"账本"**）

#### 1.0 同步 canonical probe.py(**绝对前提,不准跳**)

每次进 skill,**第一件事**是把 canonical 的 probe.py 同步到测试目录:

```bash
cp ~/.claude/skills/geo-probe/probe.py <测试目录>/probe.py
```

**为什么必须做**:测试目录里可能残留旧版 probe.py(之前手改过、复制过、或不同 schema 版本)。本地旧版 probe.py 的 docstring 和行为可能跟当前 SKILL.md 不一致——agent 跟着旧 docstring 走 = 静默用错 schema(bambulab v3 实测踩过这个坑,citations 写成域名不是 URL)。

**校验同步成功**(开跑前必须跑):

```bash
grep -c "URL 列表(不去重" <测试目录>/probe.py
# 必须输出 1,否则 cp 没生效,停手
```

#### 1.1 基本输入

1. **queries.yaml**（路径或粘贴内容）——schema 要符合 geo-queries 的输出
2. **输出目录**——默认 = `queries.yaml` 所在的目录。**所有相关文件（queries.yaml / probe-plan.yaml / probe-results-*.yaml / analysis.md）都假设在同一目录**——这是 `geo-analyze` 后续对账的前提。
3. **你（agent）有没有浏览器工具**——没有就停下来告诉用户："这个 skill 需要 agent 有浏览器能力（Claude-in-Chrome / Codex 浏览器 / 别的 MCP），装上再调"
4. **延迟范围**（可选）——默认 `--min 20 --max 60` 秒之间随机。**不允许设成 0 或 < 5 秒**。

#### 1.2 probe-plan.yaml：先 check，再决定怎么走

在同目录下找 `probe-plan.yaml`：

**情况 1：plan 不存在 → 这是首次 probe，先创建 plan**

问用户：

> 这是这个品牌的第 1 次 probe。开始前先记一下你**整次测试计划测哪几个 LLM**（用来后续 analyze 时对账，防止漏跑）。
> 预设可选：Kimi / 豆包 / DeepSeek / 百度文心 / 千问 / 元宝
> 也可以加自定义 LLM（给我 name + url）。
> 计划列表？

拿到列表后,**先写 probe-plan.yaml**（不要等跑完才写）：

```yaml
brand: <品牌名>
queries_file: <queries.yaml 的相对/绝对路径>
created_at: <ISO timestamp>

planned_llms:
  - Kimi
  - 豆包
  - DeepSeek

completed: []        # 跑完一个 append 一个

# 自定义 LLM 单独记
custom_llms: []      # [{name, url, notes}, ...]
```

接着问"这次先跑 planned_llms 里的哪一个？"。

**情况 2：plan 已存在 → 接续跑**

读 plan，算出 `pending = planned_llms - [c.llm for c in completed]`：

- 如果 `pending == []` → 报给用户："plan 显示全部 LLM 已跑完。要重跑哪一个？（重跑会覆盖该 LLM 的 probe-results）" → 等用户明示
- 否则 → "plan 显示还差这些没跑：[pending]。这次跑哪一个？"

**用户选定的 LLM 必须在 plan.planned_llms 里**。不在就停下问："这个 LLM 不在原计划里，要把它加进 plan.planned_llms 吗？"——别擅自加。

#### 1.3 确定本次 LLM 的入口 URL

预设直接用内置 URL（Kimi/豆包/DeepSeek/百度文心/千问/元宝）；自定义 LLM 从 plan.custom_llms 里读 url。

#### 1.4 确定输出路径

默认 `<output-dir>/probe-results-<llm-slug>-<date>.yaml`。slug 用小写 ASCII（kimi / doubao / deepseek / baidu / qwen / yuanbao；自定义自取）。

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
4. 问 q001（**注意：q001 是 品牌识别 类，会直接点名品牌**），等回答完整出现
5. 按第 4 步规则生成 summary + 抽 citations + 组 result block，`echo "<block>" | python3 probe.py append <output-path>`
6. 让用户瞄一眼："第 1 条跑通了，target_brand.mentions=N / sentiment=X。继续跑后面 4 条 品牌识别 吗？"

用户点头后再继续。

### 4. 跑 q002-q005（剩下 4 条品牌识别）

按第 5 步同样流程跑 q002 / q003 / q004 / q005，每条之间走 `probe.py wait`。

**跑完 q005 必须中场汇报**（这是关键 GEO 信号检查点）：

读一遍输出文件,统计 q001-q005 的 `target_brand.mentions` 和 `sentiment`,按以下三种情况报给用户:

**情况 A — 完全 0 收录**（5 条 mentions 全 0）
> 5 条 品牌识别 跑完，**目标品牌 `<品牌名>` 在 <LLM> 上完全没被识别**（5 条 mentions 全 0）。
> 这是 0 收录信号。**剩下 25 条会变得更有价值**——用来摸清:
> - 这个垂类里谁占位（看竞品在 探索发现 / 选型推荐 类的出现）
> - 模型在这个领域引哪些站（citations）→ 给 `geo-channels` 当输入,告诉你该往哪发内容
> - 哪些 prompt 是"该出现但没出现"的零命中机会
> 默认继续跑（推荐），还是停在这里？

**情况 B — 误识别**（mentions ≥ 1 但 sentiment 含 negative，notes 标了"误识别"）
> 5 条 品牌识别 跑完，**模型把 `<品牌名>` 串到了另一家公司**。
> 这是误识别信号。剩下 25 条照常跑，可以告诉你模型在"正确语境"下是否会自然提到你（vs 提到那家串掉的同名公司）。
> 默认继续跑（推荐），还是停在这里？

**情况 C — 识别正确**（多数 mentions ≥ 1 且无误识别）
> 5 条 品牌识别 跑完，模型识别正确，target_brand 平均 mentions=N / 主流 sentiment=X。
> 剩下 25 条照常跑——主要看自然提及率和竞品排名。
> 继续吗？

**所有情况下,默认推荐"继续"**——不要因为 0 收录就劝用户停。停了就拿不到 actionable。

用户点头后再进入第 5 步。

### 5. 跑剩下的 25 条（q006-q030）

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

6. **抽 citations**(两步,**citations 字段现在存 URL,不存域名,且不去重**——同一域名多个 URL 全保留,这是"该渠道值得多投放"的信号源):
   a. 走第 6.5 节的 **per-LLM Recipe**:操作浏览器点开 sources 面板 → 执行对应 JS extractor → 下载 yaml → Bash 读 → 直接拿 URL 列表(不要 `urlparse` 提域名)
   b. 兜底:`echo "<answer>" | python3 probe.py extract-citations` 抓正文里偶现的裸 URL(也是输出 URL 不是域名)。两边合并(URL 级去重——同一 URL 重复出现只算 1 次;但同域名多个 URL 全保留)
   c. **强制日志**(便于 verify-log 排查):
      ```
      python3 probe.py log <log-path> \
        --qid q006 --intent 选型推荐 --llm DeepSeek --recipe deepseek \
        --panel-opened true --urls-found 10 --domains-unique 10
      ```
      `--urls-found` = panel 里看到多少条原始 URL;`--domains-unique` = **最终写入 citations 的条数**(语义已变成"citations 列表长度",名字保留向后兼容;agent 直接传 `len(citations)`)。`log-path` = `probe-log-<llm-slug>-<date>.jsonl`,与 probe-results 同目录。**每条 query 必须 log 一次**——这是 verify-log 排查"recipe 没真跑"的唯一证据,绕过它 = 数据污染
7. **品牌识别类（`intent: 品牌识别`）的特殊处理**：
   - LLM 完全没识别（说"不知道"）→ `target_brand` 全 null，notes 写"0 收录"
   - LLM 把品牌**串到另一家同名公司**了 → notes 写明"误识别"（**关键 GEO 信号**），`target_brand.mentions` 仍记字面次数但 sentiment 标 negative
   - LLM 识别正确 → 正常记
8. **描述性提及单独记 notes**（不进 mentions 计数）：如 LLM 说"一家做具身智能小脑的初创"且画像吻合用户品牌，在 notes 里写"描述性提及：'...原句...'"
9. **追加结果**：组装 result block → `echo "<block>" | python3 probe.py append <output>`（每条立刻持久化）
10. **等下一条**：`python3 probe.py wait --min <X> --max <Y>`（默认 20 / 60；这是 Python `time.sleep`，硬执行）

### 6. 失败处理：停下来问用户

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

### 6.5 抽 citations —— 必须用 per-LLM Recipe（不再依赖正文 URL 正则）

**关键认知**(2026-05-30 实测验证):

- **中文 LLM 的引用源主要在 sources 面板的 React state 里**,**正文里只有裸名字或裸域名**(如"知乎"、"36氪"、"www.stcn.com",**几乎都不带 `https://` 前缀**)
- 老 `probe.py extract-citations` 的 URL 正则**对 Qwen / DeepSeek / Kimi / 豆包 全部失效**——只能抓到正文里偶然出现的完整 `https://...`(罕见)
- 真实数据在 sources 面板,需要**逐 LLM 写抽取脚本**

**新流程**:每条 query 答完 → 按下面 per-LLM recipe 操作浏览器抽 URL → 落入 result block 的 `citations`。**citations 字段存 URL 列表(不去重)**——同一域名多个 URL 全保留,频次本身是"该渠道权重"的信号。同时跑 `probe.py extract-citations` 作为兜底,两边合并(URL 级去重)。

#### 6.5.1 通用步骤

```
1. 等回答完整 (status 不再变化)
2. 找到本 LLM 的 "sources 触发器"(点击按钮 / 自动展开)
3. 抓到 React state 或 DOM 里的 URL 列表
4. 用 Blob/download 把列表存盘 → Bash 读 → 提取域名
   (避免 javascript_tool 返回值被 harness 的 token 屏蔽)
5. 与 probe.py 兜底结果合并去重
```

#### 6.5.2 Recipe: Qwen 千问 (`https://chat.qwen.ai`)

- **登录要求**:登录(扫码)。游客无聊天能力
- **联网搜索**:默认开,无需手动切换
- **Sources 触发器**:回答末尾的 **`+N`** 按钮(显示 favicon + 数字),点击展开右侧 "搜索来源 · N" 面板
- **数据位置**:右侧面板的 `.sources-item-wrap` 元素的 React fiber **深度 ~6** 的 `WebSearchOrigins` 组件,`memoizedProps.listData[]` 含完整 `{url, hostname, title, snippet, date}`

JS 提取脚本(在浏览器 console / `javascript_tool` 执行):

```javascript
(() => {
  const item = document.querySelector('.sources-item-wrap');
  if (!item) return { error: 'sources panel not open' };
  const fk = Object.keys(item).find(k => k.startsWith('__reactFiber'));
  let f = item[fk]; let d = 0;
  while (f && d < 30) {
    if (f.memoizedProps && f.memoizedProps.listData) {
      const data = f.memoizedProps.listData;
      const yaml = `total: ${data.length}\nsources:\n` +
        data.map((s, i) => `  - ${i+1}: ${s.url}`).join('\n');
      const blob = new Blob([yaml], {type: 'text/yaml'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = '_qwen-sources.yaml';
      a.click();
      return { total: data.length, downloaded: true };
    }
    f = f.return; d++;
  }
  return { error: 'listData not found' };
})()
```

- **典型产出**:60-90 个完整 URL,40+ 唯一域名
- **验证**:返回的 `total` 应该 ≥ panel 标题里的 "+N" 数字

#### 6.5.3 Recipe: DeepSeek (`https://chat.deepseek.com`)

- **登录要求**:登录(账号或邮箱)
- **联网搜索**:输入框下方的 **"智能搜索"** 按钮必须高亮(蓝色) → 否则不联网
- **Sources 触发器**:回答末尾的 **"N 个网页"** 按钮,点击右侧滑出 "搜索结果" 面板(class `._26c5bc2`)
- **数据位置**:面板内**标准 `<a href>` 元素**,直接抓即可——最简单

JS 提取脚本:

```javascript
(() => {
  const panel = document.querySelector('._26c5bc2');
  if (!panel) return { error: 'panel not open — click "N 个网页" first' };
  const anchors = Array.from(panel.querySelectorAll('a[href]'))
    .filter(a => !a.href.includes('chat.deepseek.com'));
  const urls = [...new Set(anchors.map(a => a.href))];
  const yaml = `total: ${urls.length}\nsources:\n` + urls.map((u, i) => `  - ${i+1}: ${u}`).join('\n');
  const blob = new Blob([yaml], {type: 'text/yaml'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = '_deepseek-sources.yaml';
  a.click();
  return { total: urls.length, downloaded: true };
})()
```

- **典型产出**:5-15 个 URL(DeepSeek 比 Qwen 引用源更精炼)
- **注意**:`._26c5bc2` 是 hash class,**Web 版迭代可能变**——如果失效,改用 `[class*="search-result"]` 或找标题"搜索结果"的最近祖先容器

#### 6.5.4 Recipe: Kimi (`https://www.kimi.com`)

- **登录要求**:登录(手机/微信)
- **联网搜索**:K2.6 快速 / 思考模型默认带搜索;输入 "/" 不需要主动开
- **Sources 触发器**:回答末尾的 **"引用"** 按钮(旁边带 3-4 个 favicon),点击右侧滑出 "引用来源 N" 面板
- **数据位置**:面板内**标准 `<a href>`**,但**会混入 Kimi 自家域名**(需黑名单过滤),且 panel 显示数 ≥ 实际可提取 URL 数(部分源是图片/视频/PDF 无 href)

JS 提取脚本:

```javascript
(() => {
  const title = Array.from(document.querySelectorAll('*'))
    .filter(el => el.children.length <= 3 && (el.textContent || '').includes('引用来源') && (el.textContent || '').trim().length < 30)[0];
  if (!title) return { error: 'panel not open — click "引用" first' };
  let panel = title.parentElement;
  while (panel && panel.children.length < 8 && panel.parentElement) panel = panel.parentElement;
  const blacklist = ['kimi.com', 'moonshot.cn', 'mokahr.com', 'chinaums'];
  const anchors = Array.from(panel.querySelectorAll('a[href^="http"]'))
    .filter(a => !blacklist.some(b => a.href.includes(b)));
  const urls = [...new Set(anchors.map(a => a.href))];
  const yaml = `total: ${urls.length}\nsources:\n` + urls.map((u, i) => `  - ${i+1}: ${u}`).join('\n');
  const blob = new Blob([yaml], {type: 'text/yaml'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = '_kimi-sources.yaml';
  a.click();
  return { total: urls.length, downloaded: true };
})()
```

- **典型产出**:5-12 个 URL(panel 标题数字会更高,差额是无 href 的源)
- **验证**:如果产出 0,检查 panel 是否真打开了(可能"引用"按钮点错位置)

#### 6.5.5 Recipe: 豆包 Doubao (`https://www.doubao.com`)

- **登录要求**:**必须登录**(手机号/抖音)
- **联网搜索**:**默认无!** 必须切到 "更多" 菜单里的 **"深入研究"** 模式才有联网;"快速 / 思考 / 专家" 三种基础模式**纯靠模型记忆,不联网**
- **重要结论**:**游客模式或基础模式下,豆包回答必然 0 引用源**——这不是 probe pipeline 的 bug,是平台不暴露这个能力
- **Sources 触发器**:深入研究模式下应有引用面板,**待真实数据复测**(本次未实测,因游客模式被弹窗拦截)

**实操建议**:跑豆包 probe 前必须确认两件事:
- 用户账号已登录
- 已切到"深入研究"模式(`更多` → `深入研究`)

如果用户不愿登录,**跳过豆包,在 plan.completed 里把它标 `skipped: 平台需登录+深入研究模式`**,不要硬跑——会拿到 0 引用的脏数据污染 analyze。

JS 提取脚本(占位,需登录后实测补完):

```javascript
// TODO: 豆包深入研究模式实测后补
(() => { return { error: 'recipe not finalized — log in and run 深入研究 first, then update SKILL.md §6.5.5' }; })()
```

#### 6.5.6 兜底:`probe.py extract-citations`

按上面 recipe 抽完后,**仍跑一遍** `echo "<answer>" | python3 probe.py extract-citations` 把正文里的裸 URL(罕见但偶尔有)合并进 citations。两边按 URL 级去重(同 URL 出现两次只算 1 次;**不要按域名去重**——同域名多个 URL 全保留)。

---

### 7. 输出格式（`probe.py` 维护，你只需理解 schema）

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

    citations:                       # URL 列表(不去重;同域名多个 URL 全保留)
      - https://36kr.com/p/123456
      - https://36kr.com/p/789012
      - https://zhuanlan.zhihu.com/p/4567890

    notes: null                      # 描述性提及 / 误识别 / 其他特殊情况

  - query_id: q017   # 失败的 query 也要记
    intent: 选型推荐
    text: <原问题>
    status: error
    error_message: <具体什么错>
    summary: null
    citations: []
```

### 8. 跑完更新 probe-plan.yaml + 总结

**第 0 件事(强制)**:跑 verify-log 检查这次 probe 的 citations 健康度:

```
python3 probe.py verify-log <log-path>
```

输出会按 LLM 给出 panel_opened 比例、domains/query 的 min/median/max、以及"低于 expected_min_domains"的异常清单。

**对待异常的硬规则**:
- **无异常(exit code 0)** → 数据可用,继续后面步骤
- **有异常(exit code 2)** → **必须报给用户**:
  > 这次 probe 有 K 条 query 的 citations 数低于预期(详见 verify-log 输出)。可能原因:
  > - per-LLM recipe 没真的执行(只用了正文 URL 正则)
  > - sources 面板没成功打开(button 点错位置 / 还没渲染)
  > - 那条 query 模型本来就只引了少数源(正常)
  >
  > 选项:
  > - a) 我重跑这 K 条(指定 qid 列表)
  > - b) 接受异常,继续往下走(数据会偏低,analyze 会受影响)
  > - c) 整个 LLM 这一轮重跑

**不允许"看见 ⚠ 还往下走且不报"**——verify-log 就是为了堵这种情况设计的。

**第一件事：更新 plan**。把刚跑完的 LLM 追加到 `completed`：

```yaml
completed:
  - llm: <LLM 名>           # 必须与 planned_llms 里的写法一致
    file: ./probe-results-<llm-slug>-<date>.yaml
    probed_at: <ISO timestamp>
```

**手动编辑 plan.yaml** 即可（YAML 简单,Edit 工具读改写都没问题；不需要单独 Python 命令）。

**第二件事:总结 + 报 plan 进度**。读一遍输出文件 + 重读 plan,给用户：

> Probe 完成: **<LLM>**
> - 输出文件: <路径>
> - 成功 <N> / 失败 <M>
> - 目标品牌 **<品牌名>** 命中 <X> 条（<X/N> %）
> - 出现最多的竞品: <前 3 个>
> - 引用源最常见的域名: <前 5 个>
>
> **Plan 进度: <M>/<N> 完成,还差 <K> 个: [pending list]**
>
> 下一步:
> - 还有 pending 的 LLM → 推荐**继续跑下一个**(直接说 LLM 名,我接着调本 skill)
> - 全部跑完 → 用 `geo-analyze` skill 出 visibility 报告

**这一步是缺口防漏的关键**——用户看到 "还差 K 个" 就不会以为已经齐了。

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
  从 stdin 读文本，抽出 URL，输出 URL 列表(不去重——同 URL 出现多次保留多次,与正文一致)。

python3 probe.py log <jsonl-path> --qid <q006> --intent <intent> --llm <name> \
                  --recipe <qwen|deepseek|kimi|doubao|fallback> \
                  --panel-opened <true|false> --urls-found <N> --domains-unique <N> \
                  [--note <text>]
  追加一条 JSONL 抽取日志。每条 query 抽完 citations 后必须 log 一次。

python3 probe.py verify-log <jsonl-path>
  读日志,按 LLM 输出健康度报告;若有 query 的域名数低于
  EXPECTED_MIN_DOMAINS 阈值,exit code 2 + 标记 ⚠ ANOMALIES。
  跑完 probe 后必须执行(见第 8 步第 0 件事)。
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
      - https://36kr.com/p/3271845
      - https://36kr.com/p/3299110     # 同域名多个 URL 都保留(频次=权重)
      - https://zhuanlan.zhihu.com/p/892341127
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
- 不要因为 q001-q005 的 品牌识别 显示"0 收录"就劝用户停掉——剩下 25 条恰恰更有价值
- 不要跳过 q005 后的中场汇报（这是关键 GEO 信号检查点）
- 不要在浏览器工具失效 / 撞验证码时硬撑或编造答案
- 不要在一个对话里串问多条（会污染上下文）
- 不要算分、出报告、做品牌对比——那是 `geo-analyze` / `geo-report` 的事
- 不要并行跑多个 LLM——一次跑一个，要测多个就调多次
- 不要存全文（schema 改了，只存 `answer_chars` + summary；想复核就重跑）
- 不要把描述性提及计入 mentions（mentions 只算字面出现，描述性提及进 notes）
- **不要绕开 `probe.py wait`**——不要把 `--min --max` 都改成 0 或 < 5
- **不要自己手写 YAML 追加**——必须走 `probe.py append`（防止格式坏掉）
- **不要使用测试目录里残留的旧 probe.py**——开跑前**必须** `cp ~/.claude/skills/geo-probe/probe.py <测试目录>/`(见第 1.0 节)。本地版本的 docstring 可能与 SKILL.md 已规定的 schema 不同步,跟着旧 docstring 走 = 静默用错 schema
- **不要跳过 `probe.py log`**——每条 query 抽完 citations **必须** log 一次。少 log 一条,verify-log 就抓不到"recipe 没真跑"的证据
- **不要在 verify-log 报 ⚠ ANOMALIES 时静默继续**——必须按第 8 步硬规则报给用户,让用户决定 a/b/c
