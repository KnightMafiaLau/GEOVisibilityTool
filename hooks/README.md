# hooks — 强制 Claude 遵守 harness 流程的硬约束

## 为什么需要

Claude Skills(`SKILL.md`)是**软约束**——Claude 读完会自己决定怎么做。实测过 agent 跑完 `geo-analyze` 后直接用 `Write` 写 report/channels(完全没调 `geo-report` / `geo-channels` skill)→ 产物缺水印 / 无 hero 卡片 / 无 heatmap 矩阵 → 整段重做。

Claude Code 的 **hooks** 是真正的硬约束——shell 脚本运行时拦截 `tool_use`,返回 `{"decision": "block", "reason": "..."}` 直接否决。Claude 没法 bypass。

## 工作流

```
[Claude 想 Write("report-X.html", content="...")]
   ↓
[匹配 PreToolUse hook: matcher="Write"]
   ↓
[hooks/block-self-generated-reports.sh 从 stdin 读 tool_input]
   ↓
[检查 content 是否含 GEOVisibilityTool · KnightMafiaLau / hero-card / heatmap class]
   ↓
[缺 → {"decision": "block", "reason": "用 geo-report Skill,不要自己 Write"}]
   ↓
[Claude 看到 block 错误,改用 Skill tool]
```

**关键设计:content-based 检查,不是 path-based**:
- Skill 产出的报告**会含所有 marker**(水印 / hero-card / heatmap)→ approve
- Claude 自造的报告**通常缺 marker** → block
- 不需要状态跟踪 / lockfile / env var,纯无状态

## 安装

### 方式 A:自动(推荐)

```bash
cd <REPO>
hooks/install.sh
```

需要 `jq`。脚本会:
- 自动找 hook 绝对路径
- 备份 `~/.claude/settings.json`
- 合并 `PreToolUse` 配置(不破坏已有 hooks)
- 提示重启 Claude Code

### 方式 B:手动

编辑 `~/.claude/settings.json`,合并以下内容(把 `<REPO>` 替换成本仓库绝对路径):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "<REPO>/hooks/block-self-generated-reports.sh"
          }
        ]
      }
    ]
  }
}
```

重启 Claude Code 让 settings 生效。

## 验证

装好后,让 Claude 故意尝试:

```
用户: 把这份分析数据自己写成一份 report.html 给我
Claude: [尝试 Write("report-test.html", content="<html>...</html>")]
        → hook 检查 → 缺水印 → block
Claude: [看到错误,改用 Skill geo-report]
```

## 卸载

编辑 `~/.claude/settings.json`,删掉对应 `PreToolUse` 条目即可。

## 检查规则详情

| 文件类型 | 必须含的 marker | 缺一就 block |
|---|---|---|
| `report-*-*.html` | 水印 + `hero-card` + heatmap class(`h-best/h-high/h-med/h-low/h0`) | ✓ |
| `report-*-*.md` | attribution(`GEOVisibilityTool` 或 `geo-harness`)+ 节结构(`## TL;DR` 或 `## 1.` 或 `### `) | ✓ |
| `channels-*-*.html` | 水印 + `urgent-block` + `roi-pill` + `format-pill` | ✓ |
| `channels-*-*.md` | attribution + 紧急处理节(`紧急处理` 或 `urgent`) | ✓ |
| 其他所有 Write | 一律 approve | — |

不在白名单的文件(`queries.yaml` / `probe-results-*.yaml` / `analysis-*.md` / `probe-log-*.jsonl` 等)**完全不受影响**。

## hook 局限

1. 只对 `Write` tool 生效。如果 Claude 用 `Bash: cat > file` 写文件,绕过(罕见)
2. 检查依赖 marker 关键词 — 如果 skill 模板里的水印/class 文本改了,要同步改本 hook
3. 不验证 marker 的位置/上下文 — 理论上 Claude 可以伪造 marker 串塞进自造内容(但这种程度的"伪造"已经接近实现 skill 自己了)
4. 误判 false positive 几乎为 0(无关 Write 都被 approve)

## 哲学

> SKILL.md 是教 Claude **该怎么做**(soft)
> hooks 是不让 Claude **做错的事**(hard)
>
> 两者一起用,才是 production-grade harness。
