# geo-harness

> **AI 品牌可见度测量与投放策略工具集** · 端到端 GEO(Generative Engine Optimization)分析 harness
> 由 6 个 Claude Skills 组成,**测真实 LLM、出可信报告、给可执行建议**

[![GitHub](https://img.shields.io/github/stars/KnightMafiaLau/geo-harness?style=social)](https://github.com/KnightMafiaLau/geo-harness)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 一、GEO 是什么

**Generative Engine Optimization**(生成式引擎优化)—— 让品牌在 AI 搜索的回答里"被自然提到、被高位推荐、被作为 canonical source 引用"的工程化方法论。

它**不是 SEO 的升级版**——SEO 优化的是搜索引擎结果页的排名,GEO 优化的是 LLM 回答内容里的品牌叙述权重。两者底层逻辑不同:
- SEO 面向"链接被点击",GEO 面向"品牌被复述"
- SEO 的反馈是 PV / CTR,GEO 的反馈是 LLM 答案里有没有你的名字、排第几、上下文情绪如何
- SEO 的工具链成熟(Google Search Console、Ahrefs、SEMrush 等),GEO 的工具链还在早期

### 1.1 GEO 的完整链路(9 步)

GEO 完整闭环按"用户提问 → 品牌被 AI 推荐"的因果链可拆为 9 步(参考 [WaytoAGI 直播 · 姚金刚分享的"GEO 完整路径图"](https://waytoagi.com/)):

```
1. 用户搜索问题
   用户向 AI 提出真实问题(如"国内做 X 的公司有哪些值得关注?")

2. AI 进行意图拆解
   AI 理解用户真正问什么,拆出关键词、场景、对象、具体条件

3. AI 先给出初始答案
   此时 AI 可能推荐了竞品 A / B / C 等,但你的品牌未出现 ← GEO 缺口出现

4. 反查引用来源与信源偏好
   AI 引了哪些站、什么类型的内容、什么格式偏好?(评测/FAQ/对比文/案例)
   → 这一步反推出"模型在该垂类的知识来源结构"

5. 制定内容策略
   基于信源偏好,决定该往哪些渠道投放、什么内容形态、什么主题

6. 生成适配 AI 收录的内容
   品牌介绍 / 功能对比 / 使用教程 / FAQ / 客户案例 / 行业趋势 等
   → 这是内容生产层的工作

7. 发布到 AI 偏好的平台
   官网 / 问答社区 / 行业媒体 / 博客专栏 / 自媒体矩阵 / 视频站 等
   → 这是分发层的工作

8. AI 抓取、索引、吸收
   内容被 AI 搜索系统抓取、理解,进入候选知识合集

9. 再次搜索,品牌被推荐
   下一轮 probe 验证:同样的 query,你的品牌是否进入了回答?
   → 完成闭环
```

### 1.2 GEO 的本质

> **不是直接操控 AI,而是通过更合适的内容、更合适的平台和更持续的分发,让品牌进入 AI 可引用的知识网络。**

这意味着两个工具层是**互补**而非竞争的关系:

| 层 | 解决什么 | 代表工具 |
|---|---|---|
| **测量与策略层**(步骤 1-5) | 测当前可见度、反查信源偏好、出投放策略 | **本项目 geo-harness** |
| **生产与分发层**(步骤 6-7) | 自动化生成内容、多站点分发、CMS 管理 | [GEOFlow](https://github.com/yaojingang/GEOFlow) 等 |

**完整 GEO 闭环** = `geo-harness` 测出缺口和方向 → 团队/CMS 生产并分发 → 下一轮 `geo-harness` 验证改变 → 持续迭代。

---

## 二、本工具集做什么

`geo-harness` 是 6 个 Claude Skills 组成的端到端测量 + 策略工具集。**专注 GEO 9 步路径里的 1-5 步**:

```
                ┌─────────────────────────────────────────────────────┐
                │  geo-harness 工具集(本项目)                         │
                ├─────────────────────────────────────────────────────┤
[用户:测我品牌] │ 1) geo-queries  生成 30 条真实用户问题              │
                │ 2) geo-probe    去问真实 LLM(Qwen/DeepSeek/Kimi…)   │
                │ 3) geo-analyze  算 visibility 分数 / 竞品 / 引用源  │
                │ 4) geo-report   出 CEO 风格诊断报告(HTML)           │
                │ 5) geo-channels 出投放建议(该投哪 / 什么形态)        │
                │ 6) geo-harness  总入口编排,一句话触发全流程         │
                └─────────────────────────────────────────────────────┘
                                       ↓
                          (交给内容团队 / GEOFlow / CMS)
                                       ↓
                       [步骤 6-9: 生产 / 分发 / 抓取 / 验证]
                                       ↓
                          (下一轮 geo-harness 验证)
```

### 与其他 GEO 工具的关系

- **vs Topify**(SaaS 测量服务):本项目是开源自托管,数据全在本地,可定制各模块;Topify 是云服务报告订阅
- **vs GEOFlow**(开源 CMS):**完全互补**——GEOFlow 关注步骤 6-7 的内容生产 + 多站分发,本项目关注步骤 1-5 的测量 + 策略。建议组合使用
- **vs 手动 GEO 咨询**:本项目把"诊断 + 策略"这部分工程化,从依赖个人经验转向数据驱动

---

## 三、6 个模块详解

### 模块 1: `geo-queries` — 生成测试问题

给一个品牌(中文名 / 行业 / 垂类 / 一句话定位 / 竞品 2-3 个),生成 **30 条真实用户问题**,按 6 类意图分布:

- 品牌识别(q001-q005,query 含品牌名,测 LLM 是否知道你)
- 探索发现(q006+,用户摸索陌生领域)
- 选型推荐(挑工具/服务)
- 对比评估(A vs B,结构性排除 target)
- 了解原理(普及性技术问题)
- 采购投资(B2B 找供应商 / 投资人调研)

每类内部混合"短抽象"(15-40 字)和"长场景具体"(80-150 字)两种风格,严格禁复合题、禁 multiple-choice 引导式。

### 模块 2: `geo-probe` + `probe.py` — 真实 LLM 抓取

逐条把问题问到目标 LLM 的**网页端**(浏览器 MCP),记下:
- 完整回答 + 命中品牌(目标 + 竞品 + 别名) + 情绪 + 排名
- **结构化引用源**(每个 LLM 一套 React fiber / DOM scrape recipe,bypass chat sanitizer)

内置 6 个 LLM 预设:**Kimi / 豆包 / DeepSeek / 百度文心 / 千问 / 元宝**;支持自定义 LLM。配套 `probe.py`(Python stdlib only,机械活)。

**关键设计**:
- q001-q005 跑完中场汇报(0 收录 / 误识别 / 正确 三种情况)
- 每条 query 强制 log,跑完 `verify-log` 检查异常
- 跨 query 随机 20-60 秒间隔防风控

### 模块 3: `geo-analyze` — 算分 + 画像

读 probe-results 算 6 个核心指标:

- **Visibility Score 0-100**(加权:自然提及 40 + 识别 30 + 排名 20 + 情绪 10)
- 识别率 / 自然提及率 / 平均排名 / 推荐率 / 正向情绪率
- 竞品分布(top 10,中英文名合并)
- **引用源画像** — channel-level(域名 top 15)+ article-level(高频 URL top 10)+ per-LLM × per-intent 偏好矩阵
- 高价值零命中清单(商业意图 × 竞品占位 × 自身缺席 三条件筛)

**核心 schema**:`citations` 字段存 **URL 列表(不去重)**,同域名多 URL 全保留——这是后续"广覆盖 channel vs 单篇热文 canonical source"判别的基础。

### 模块 4: `geo-report` — CEO 视角报告

把 analyze 数据渲染成给决策人看的报告。**双输出**:`.md`(可编辑)+ `.html`(自包含、带作者水印、浏览器 Cmd+P 可存 PDF)。

**Topify-inspired 风格**:
- Hero metrics 3 卡片(Visibility / 总提及 / 关键指标)
- **报忧 / 报喜双卡片**(red + green,各 3-5 条加粗短句)
- 竞品对比卡片 grid(自己蓝边高亮)
- LLM × 品牌 heatmap 矩阵
- 提示词 × LLM heatmap 矩阵
- 引用源 channel top 15 + 两 LLM 信源结构对比

**严格边界**:**不出"下一步建议 / 投放方案"** —— 那是 geo-channels 的事。

### 模块 5: `geo-channels` — 投放策略

把 analysis 翻译成 actionable 投放建议。**双输出 .md + .html**,沿用 CEO 风格。

7 节结构:
- **🔥 紧急处理**(负面 sentiment / 误识别 priority,即使无触发也保留节)
- **优先 channel 投放清单 top 10**(grid,带 ROI + 投放形态 pill)
- **Per-LLM 适配策略**(内容偏好 + 渠道偏好 双维度)
- **竞品反位攻关**(对手官网已占位 LLM 信源池 → 反位投放)
- **零命中 query 攻关**(每条高价值零命中 → 该投哪 + 什么内容)

**核心剔除规则**:
- 竞品官网/自有内容站(creality.com 等)绝不进 channel grid
- 搜索引擎/索引类站(patents.google / scholar 等)不进 grid,作为 IP 战略 signal

ROI 定性 high / med / low,公式公开,无伪精度;投放形态 mapping 14 类硬编码(知乎专栏→深度文 / smzdm→购买决策 / B 站→视频 / ...)。

### 模块 6: `geo-harness` — 总入口编排

**一句话触发,6 phase + 5 个用户确认门**:

```
Phase 1: 拿品牌信息 → geo-queries → queries.yaml
         [CP1: 用户审 queries]
Phase 2: 问 planned LLMs → 写 probe-plan.yaml
         [CP2: 用户确认 plan + ETA]
Phase 3: 对每个 LLM 调 geo-probe(顺序,非并行)
         [CP3 per-LLM: 跑完一个,问继续下一个]
Phase 4: geo-analyze → analysis.md
         [CP4: 用户看顶层数]
Phase 5: geo-report → report.{md,html}(自动打开)
         [CP5: 用户看 report]
Phase 6: geo-channels → channels.{md,html}(自动打开)
         [完成: 产物清单]
```

**支持断点续跑**——从测试目录现有文件状态推断当前阶段。失败绝不自动重试。所有 sub-skill 通过 Skill tool 调用,不复制逻辑。

---

## 四、安装与使用

### 4.1 前置要求

- **Claude Code 客户端**(`claude.ai/code`)或任何支持 Anthropic Skills 的 Claude 客户端
- **浏览器 MCP**:probe 阶段需要 Claude-in-Chrome 或其他浏览器 MCP(用于操作真实 LLM 网页端)
- **Python 3** stdlib(`probe.py` 用,不需要额外依赖)

### 4.2 安装

```bash
# 克隆仓库
git clone https://github.com/KnightMafiaLau/geo-harness.git
cd geo-harness

# 装到 Claude 的 skills 目录(6 个模块)
mkdir -p ~/.claude/skills
cp -r skills/geo-queries skills/geo-probe skills/geo-analyze \
      skills/geo-report skills/geo-channels skills/geo-harness \
      ~/.claude/skills/

# 重启 Claude 客户端让 skill 列表刷新
```

### 4.3 端到端使用(推荐)

```
用户: 测我品牌 X 的 AI 可见度
Claude: [触发 geo-harness skill]
       问 5 项品牌信息 → 出 queries → 用户审
       问 planned LLMs → 写 plan → 用户确认
       对每个 LLM 调 geo-probe → ...
       analyze → report(自动打开 HTML)→ channels(自动打开 HTML)
       完成,给产物清单
```

**典型耗时**:
- 2 个 LLM(DeepSeek + Qwen):约 60-90 分钟(probe 是主要耗时)
- 完整 4 个 LLM:约 2-3 小时

### 4.4 分模块使用(高级)

每个模块都可独立调用:

```
# 只生成测试问题(不实际 probe)
用户: 生成 GEO 测试问题
Claude: [调 geo-queries skill]

# 只对已有 probe-results 出报告
用户: 把这份 probe-results 算成 analysis
Claude: [调 geo-analyze skill,传 yaml 路径]

# 已有 analysis,只出 CEO 报告
用户: 把这份 analysis 渲染成 report
Claude: [调 geo-report skill]
```

### 4.5 断点续跑

```
用户: 接着跑拓竹科技那个 GEO 测试
Claude: [调 geo-harness skill]
       读测试目录 → 推断当前阶段(如 Phase 3 跑完 1/3 LLM)
       报当前状态 → 问"继续跑剩下的 LLM 吗?"
       从断点继续
```

---

## 五、产物示例

完整跑一次 harness 后,测试目录下会有:

```
my-brand/
├── queries.yaml                          # 30 条测试问题
├── probe-plan.yaml                       # 测试账本(planned LLMs + completed)
├── probe-results-deepseek-2026-05-30.yaml  # DeepSeek 30 条结果
├── probe-log-deepseek-2026-05-30.jsonl     # DeepSeek 抓取日志(verify-log 用)
├── probe-results-qwen-2026-05-30.yaml      # Qwen 30 条结果
├── probe-log-qwen-2026-05-30.jsonl
├── analysis-my-brand-2026-05-30.md         # 机器可读分析数据
├── report-my-brand-2026-05-30.md           # CEO 报告(文本)
├── report-my-brand-2026-05-30.html         # CEO 报告(HTML + 水印)
├── channels-my-brand-2026-05-30.md         # 投放建议(文本)
├── channels-my-brand-2026-05-30.html       # 投放建议(HTML + 水印)
└── probe.py                                 # canonical 镜像
```

报告样例可在 [`docs/samples/`](docs/samples/) 查看(待补)。

---

## 六、项目原则(Constitution)

详见 [CONSTITUTION.md](CONSTITUTION.md)。核心 6 条:

1. **模块独立可用** — 每个 skill 单独装上就能产生价值
2. **不强制 API key** — 默认路径不要求用户配 OpenAI/Anthropic 等 key
3. **用户先确认再动外部资源** — 跑真 LLM、下载文件等操作必须先确认
4. **SDD 是工具不是负担** — 不堆 spec.md / plan.md / research.md 文档矩阵
5. **不假装、不糊弄** — 不编结果、不绕过确认、不假装跑通
6. **模块形态:纯 skill 或 skill + 单个 Python 文件** — Python 仅做机械活、stdlib only、≤150 行

完整路线图见 [TASKS.md](TASKS.md)。

---

## 七、致谢与相关项目

- **GEO 9 步路径图**:来自 [WaytoAGI](https://waytoagi.com/) 直播,姚金刚(镜河科技 CEO)分享
- **[GEOFlow](https://github.com/yaojingang/GEOFlow)**(by 姚金刚):互补的 GEO 内容生产 + 多站分发系统,推荐组合使用
- **Topify**:商业 GEO 测量服务,报告视觉风格部分参考了 Topify

---

## 八、License

MIT License — 自由使用、修改、分发,需保留作者署名(`KnightMafiaLau`)。

报告 HTML 输出**内嵌强制水印**(`geo-harness · KnightMafiaLau`),作为 open-source attribution,无论使用场景均保留。详见 `skills/geo-report/SKILL.md` 与 `skills/geo-channels/SKILL.md` 的水印红线条款。

---

<sub>本工具集由 **KnightMafiaLau** 创建并维护 · [GitHub](https://github.com/KnightMafiaLau/geo-harness) · 问题反馈与 PR 欢迎</sub>
