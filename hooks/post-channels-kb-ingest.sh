#!/usr/bin/env bash
# GEOVisibilityTool — PostToolUse hook
# 在 Write 写完 channels-*-*.html 后,自动跑 scripts/kb.py ingest 把这次产物
# 累积到 ~/.geo-kb/kb.sqlite。harness Phase 6.5 不再依赖 Claude 主动调用,
# hook 在文件系统层面自动触发。
#
# 安装:由 hooks/install.sh 注册到 ~/.claude/settings.json PostToolUse 数组。
#
# 行为:
#   - Write 的 file_path 必须匹配 /channels-*-*.html$ → 才触发
#   - 同目录必须有 probe-plan.yaml → 才认为是 harness 跑(否则跳过)
#   - 从 probe-plan.yaml 读 vertical 字段(没有就用 "未分类")
#   - 调 scripts/kb.py ingest(kb.py 通过 hook 自身路径推断)
#   - 把 ingest 输出回写给 Claude(additionalContext),让 Claude 知道 KB 已更新

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KB_PY="$SCRIPT_DIR/../scripts/kb.py"

input=$(cat)

python3 - "$input" "$KB_PY" <<'PYEOF'
import json, os, re, subprocess, sys
from pathlib import Path

raw_input = sys.argv[1]
kb_py = Path(sys.argv[2])

try:
    data = json.loads(raw_input)
except Exception:
    sys.exit(0)

if data.get("tool_name") != "Write":
    sys.exit(0)

inp = data.get("tool_input", {})
path = inp.get("file_path", "")

# 只在 channels-*-*.html 触发(harness 最后一步)
if not re.search(r"/channels-[^/]+\.html$", path):
    sys.exit(0)

test_dir = Path(path).parent
if not test_dir.is_dir():
    sys.exit(0)

# 必须有 probe-plan.yaml(确保是完整 harness 跑出来的,而不是随手写的 channels)
plan_path = test_dir / "probe-plan.yaml"
if not plan_path.exists():
    sys.exit(0)

if not kb_py.exists():
    print(json.dumps({"additionalContext": f"[KB hook] 找不到 {kb_py},跳过 ingest"}))
    sys.exit(0)

# 读 vertical(probe-plan.yaml 里可选字段)
vertical = "未分类"
plan_text = plan_path.read_text(encoding="utf-8")
m = re.search(r"^vertical:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", plan_text, re.MULTILINE)
if m:
    vertical = m.group(1).strip()

# 跑 ingest
try:
    result = subprocess.run(
        ["python3", str(kb_py), "ingest", str(test_dir), "--vertical", vertical],
        capture_output=True, text=True, timeout=120,
    )
    out = (result.stderr or "").strip()
    if result.stdout.strip():
        out += "\n" + result.stdout.strip()
    if result.returncode != 0:
        out = f"[exit={result.returncode}]\n{out}"
    print(json.dumps({
        "additionalContext": (
            f"✓ [KB auto-ingest] 已自动 ingest {test_dir.name} 到 ~/.geo-kb/kb.sqlite\n"
            f"  vertical: {vertical}\n"
            f"  output: {out[:500]}"
        )
    }))
except subprocess.TimeoutExpired:
    print(json.dumps({"additionalContext": "[KB hook] ingest 超时(>120s),跳过"}))
except Exception as e:
    print(json.dumps({"additionalContext": f"[KB hook] error: {e}"}))
PYEOF
