# Constitution — geo-harness

这个项目"做什么、不做什么"的硬约束。任何提案违反这些原则就否决，不要 negotiate。

## 1. 模块独立可用

每个模块（skill）要能单独装、单独用，不依赖其他模块也能产出可见价值。
例子：`geo-queries` 装上就能生成问题清单，不必先装别的。

## 2. 不强制 API key

默认路径不允许要求用户配 API key。能让用户自己的 LLM（Claude / Codex）干的事，就让用户的 LLM 干。需要 key 的路径是可选的，不是默认。

## 3. 用户先确认再动外部资源

任何会"花真钱、烧 token、动用户机器"的操作（去问真实 LLM、调付费接口、写 `~/.claude` 等），都必须先让用户在对话里明确确认。不允许跳过这一步偷偷做。

## 4. SDD 是工具不是负担

我们用 SDD 的思路（先写清楚再做），但不堆 `spec.md` / `plan.md` / `research.md` / `data-model.md` / `contracts/` 这些文档矩阵。一个模块的"规格"就是它的 `SKILL.md`（+ 可选的同目录单个 Python 文件，见 #6）+ 这个 Constitution + `TASKS.md`，不需要更多。

## 5. 不假装、不糊弄

跑测试用真数据；没数据就说没数据；不会做的事就说不会做。不编结果、不假装跑通、不绕过用户的确认环节。

## 6. 模块形态：纯 skill，或 skill + 单个 Python 文件

每个模块只能是两种形态之一：

- **纯 skill**：只有一份 `SKILL.md`（适合纯判断 / 生成类任务，例如 `geo-queries`）
- **skill + Python 单文件**：`SKILL.md` + 一份同目录的 `.py` 文件（适合带机械活的任务，例如 `geo-probe` 的定时、文件追加、URL 抽取）

带 Python 时的硬约束（违反任一条就改回纯 skill 形态）：

- **单文件**——不允许多个 `.py` 分散
- **只用 Python 标准库**——不允许第三方依赖（`pip install` 触发 = 红线）
- **Python 只做机械活**：定时、文件 I/O、字符串与 URL 解析、计数、原子写
- **Python 不做**：编排、判断、流程决策——这些归 `SKILL.md` 让 Claude 干
- **≤ 150 行**——超了就是信号：你大概率把判断的活塞进了代码，停下来想想
