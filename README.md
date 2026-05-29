# geo-harness

测一个品牌在 AI 搜索里的可见度——最终目标是一套能跑端到端 GEO（Generative Engine Optimization）测试的工具：

**品牌信息 → 生成问题 → 问真实 LLM → 算分 → 出报告**

## 现状

模块 1 完成：[`skills/geo-queries`](skills/geo-queries/SKILL.md) —— 给定品牌信息，生成 30 条按 5 类意图分布的 GEO 测试问题。

完整路线图见 [TASKS.md](TASKS.md)，项目原则见 [CONSTITUTION.md](CONSTITUTION.md)。

## 用 `geo-queries` skill

复制到本地 Claude 的 skills 目录：

```bash
mkdir -p ~/.claude/skills
cp -r skills/geo-queries ~/.claude/skills/
```

然后在 Claude Code（或任何装了 skill 的 Claude）里说：

> 帮我生成 GEO 测试问题

skill 会问你 5 项输入（品牌名、行业、垂类、一句话定位、竞品），输出 30 条按 5 类（探索发现 / 选型推荐 / 对比评估 / 了解原理 / 采购投资）分好的 YAML。
