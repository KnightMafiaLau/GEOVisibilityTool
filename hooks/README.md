# hooks — 强制 Claude 遵守 harness 流程的硬约束

## 为什么需要

Claude Skills(`SKILL.md`)是**软约束**——Claude 读完会自己决定怎么做。实测过 agent 跑完 `geo-analyze` 后直接用 `Write` 写 report/channels(完全没调 `geo-report` / `geo-channels` skill)→ 产物缺水印 / 无 hero 卡片 / 无 heatmap 矩阵 → 整段重做。还有更隐蔽的:agent 干完 `geo-channels` 后忘了调 `geo-kb`,导致每次跑都是孤岛,KB 累积不起来。

Claude Code 的 **hooks** 是真正的硬约束——shell 脚本在 `tool_use` 前后被 harness 自动调用,可以 `block` 拦截,也可以 `additionalContext` 注入信息。Claude 没法 bypass。

本目录提供两个 hook,各管一段:

| hook | 时机 | 作用 |
|---|---|---|
| `block-self-generated-reports.sh` | `PreToolUse` / `Write` | 防 Claude 用 Write 自造 report/channels(缺水印就 block) |
| `post-channels-kb-ingest.sh` | `PostToolUse` / `Write` | `channels-*.html` 写完后**自动**跑 `scripts/kb.py ingest`,不靠 SKILL.md 指示 |

## 工作流

### hook #1: PreToolUse — 拦截自造报告

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

### hook #2: PostToolUse — 自动 ingest 到 KB

```
[geo-channels skill 跑完 Write("channels-*.html", ...)]
   ↓
[Write 成功后,harness 调 PostToolUse hooks]
   ↓
[hooks/post-channels-kb-ingest.sh 从 stdin 读 tool_input]
   ↓
[文件名匹配 channels-*-*.html ? 同目录有 probe-plan.yaml ? 是 → 触发]
   ↓
[读 probe-plan.yaml 的 vertical 字段(没有就 "未分类")]
   ↓
[python3 scripts/kb.py ingest <test_dir> --vertical <V>]
   ↓
[把 stdout/stderr 通过 additionalContext 回写给 Claude]
   ↓
[Claude 知道 KB 已自动更新,不用再手动调 geo-kb 来 ingest]
```

**关键设计:把 Phase 6.5 从 SKILL.md 硬要求降级为可选**:
- 之前:SKILL.md 让 Claude 跑完 channels 后**必须**调 `geo-kb` ingest,Claude 经常忘
- 现在:hook 在文件系统层面自动触发,Claude 忘了也无所谓
- 只在**完整 harness 跑**(同目录有 `probe-plan.yaml`)才触发,随手 `Write` 一个 channels.html 不会误触
- 失败 / 超时不影响 Claude 继续,只是 KB 那次没 ingest 上(下次再跑也行)

## 安装

### 方式 A:自动(推荐)

```bash
cd <REPO>
hooks/install.sh
```

需要 `jq`。脚本会:
- 自动找两个 hook 的绝对路径
- 备份 `~/.claude/settings.json`
- 合并 `PreToolUse` 和 `PostToolUse` 配置(不破坏已有 hooks)
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
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "<REPO>/hooks/post-channels-kb-ingest.sh"
          }
        ]
      }
    ]
  }
}
```

重启 Claude Code 让 settings 生效。

## 验证

### 验证 PreToolUse(防自造)

```
用户: 把这份分析数据自己写成一份 report.html 给我
Claude: [尝试 Write("report-test.html", content="<html>...</html>")]
        → hook 检查 → 缺水印 → block
Claude: [看到错误,改用 Skill geo-report]
```

### 验证 PostToolUse(自动 ingest)

跑一遍完整 harness(任意 vertical),Phase 6 写完 `channels-XXX.html` 后:

```bash
ls ~/.geo-kb/kb.sqlite   # 应该有
sqlite3 ~/.geo-kb/kb.sqlite "SELECT name, vertical FROM tests ORDER BY id DESC LIMIT 1"
# 最新一行应该就是刚跑的那个目录
```

如果 Claude 收到了类似 `✓ [KB auto-ingest] 已自动 ingest ... 到 ~/.geo-kb/kb.sqlite` 的 additionalContext,说明 hook 触发成功。

## 卸载

编辑 `~/.claude/settings.json`,删掉对应 `PreToolUse` / `PostToolUse` 条目即可。

## 检查规则详情

### PreToolUse(`block-self-generated-reports.sh`)

| 文件类型 | 必须含的 marker | 缺一就 block |
|---|---|---|
| `report-*-*.html` | 水印 + `hero-card` + heatmap class(`h-best/h-high/h-med/h-low/h0`) | ✓ |
| `report-*-*.md` | attribution(`GEOVisibilityTool` 或 `geo-harness`)+ 节结构(`## TL;DR` 或 `## 1.` 或 `### `) | ✓ |
| `channels-*-*.html` | 水印 + `urgent-block` + `roi-pill` + `format-pill` | ✓ |
| `channels-*-*.md` | attribution + 紧急处理节(`紧急处理` 或 `urgent`) | ✓ |
| 其他所有 Write | 一律 approve | — |

不在白名单的文件(`queries.yaml` / `probe-results-*.yaml` / `analysis-*.md` / `probe-log-*.jsonl` 等)**完全不受影响**。

### PostToolUse(`post-channels-kb-ingest.sh`)

| 触发条件 | 全部满足才跑 ingest |
|---|---|
| `tool_name == "Write"` | ✓ |
| `file_path` 匹配 `/channels-[^/]+\.html$` | ✓ |
| 同目录存在 `probe-plan.yaml` | ✓ |
| `scripts/kb.py` 存在 | ✓ |

读 `probe-plan.yaml` 里 `vertical: xxx` 一行作为 `--vertical` 参数,没有就用 `"未分类"`。超时 120 秒。

## hook 局限

1. 只对 `Write` tool 生效。如果 Claude 用 `Bash: cat > file` 写文件,绕过(罕见)
2. PreToolUse 检查依赖 marker 关键词 — 如果 skill 模板里的水印/class 文本改了,要同步改本 hook
3. PreToolUse 不验证 marker 的位置/上下文 — 理论上 Claude 可以伪造 marker 串塞进自造内容(但这种程度的"伪造"已经接近实现 skill 自己了)
4. PostToolUse 必须靠 `probe-plan.yaml` 来识别"这是 harness 跑出来的",所以 Phase 2 的 `geo-queries` skill 必须把 plan 写在测试目录里(已是默认行为)
5. 误判 false positive 几乎为 0(无关 Write 都被 approve / 不触发 ingest)

## 哲学

> SKILL.md 是教 Claude **该怎么做**(soft)
> hooks 是不让 Claude **做错的事**(hard,PreToolUse)
> hooks 也是替 Claude **顺手把后续事做了**(hard,PostToolUse)
>
> 三者一起,才是 production-grade harness。
