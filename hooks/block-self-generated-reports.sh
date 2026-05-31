#!/usr/bin/env bash
# GEOVisibilityTool harness 硬约束 hook
# PreToolUse on Write — 如果写的是 report/channels 文件,检查 content 是否含
# Skill 规格要求的 marker(水印/hero-card/heatmap/urgent-block 等)。
# 缺 marker = Claude 自造的(不是 skill 出的)→ block,提示用 Skill tool。
#
# 这是 "content-based" 而非 "path-based" 检查 — Skill 产出会含 marker,自造的不会。
# 不需要状态跟踪 / 不依赖 env / 不需要 lockfile。
#
# 安装:把 hooks/settings-snippet.json 内容合并到 ~/.claude/settings.json

set -euo pipefail

# 从 stdin 读 hook input(包含 tool_name + tool_input)
input=$(cat)

python3 - "$input" <<'PYEOF'
import json, re, sys

try:
    data = json.loads(sys.argv[1])
except Exception:
    print(json.dumps({"decision": "approve"}))
    sys.exit(0)

if data.get("tool_name") != "Write":
    print(json.dumps({"decision": "approve"})); sys.exit(0)

inp = data.get("tool_input", {})
path = inp.get("file_path", "")
content = inp.get("content", "")

# 检查路径是否属于受保护的产物类型
report_html_match = re.search(r"/report-[^/]+\.html$", path)
report_md_match   = re.search(r"/report-[^/]+\.md$", path)
chan_html_match   = re.search(r"/channels-[^/]+\.html$", path)
chan_md_match     = re.search(r"/channels-[^/]+\.md$", path)

if not (report_html_match or report_md_match or chan_html_match or chan_md_match):
    print(json.dumps({"decision": "approve"})); sys.exit(0)

# 准备 marker checklist
required = []
if report_html_match:
    required = [
        ("GEOVisibilityTool · KnightMafiaLau", "水印 attribution"),
        ("hero-card",   "Hero 卡片 CSS class"),
        ("h-best|h-high|h-med|h-low|h0", "Heatmap 颜色 class"),
    ]
    skill = "geo-report"
elif chan_html_match:
    required = [
        ("GEOVisibilityTool · KnightMafiaLau", "水印 attribution"),
        ("urgent-block", "紧急处理专区 CSS"),
        ("roi-pill",     "ROI pill CSS"),
        ("format-pill",  "投放形态 pill CSS"),
    ]
    skill = "geo-channels"
elif report_md_match:
    required = [
        (r"GEOVisibilityTool|geo-harness", "末尾 attribution 行"),
        (r"## TL;DR|## 1\.|^### ",         "节结构"),
    ]
    skill = "geo-report"
elif chan_md_match:
    required = [
        (r"GEOVisibilityTool|geo-harness", "末尾 attribution 行"),
        (r"紧急处理|urgent",                "紧急处理节"),
    ]
    skill = "geo-channels"

missing = [desc for pat, desc in required if not re.search(pat, content)]

if missing:
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"🚫 GEOVisibilityTool 硬约束:这个 {path.split('/')[-1]} 文件缺少 "
            f"`{skill}` skill 规定的 marker:\n\n"
            + "\n".join(f"  • 缺 {d}" for d in missing) + "\n\n"
            f"这说明你**在自己生成报告,绕过了 {skill} skill**。\n\n"
            f"正确做法:用 Skill tool 调 {skill},让它产出合规文件:\n\n"
            f"  Skill {{\n"
            f"    skill: \"{skill}\",\n"
            f"    args: \"<analysis-md 路径>\"\n"
            f"  }}\n\n"
            f"如果你确实是在 {skill} skill 内部按其完整模板写文件(应该会有所有 marker),"
            f"检查模板是不是被截断 / 没复制全。完整模板在 ~/.claude/skills/{skill}/SKILL.md。"
        )
    }))
else:
    print(json.dumps({"decision": "approve"}))
PYEOF
