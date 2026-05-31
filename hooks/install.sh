#!/usr/bin/env bash
# 安装 GEOVisibilityTool hooks 到 ~/.claude/settings.json
# 用 jq 合并 PreToolUse / PostToolUse 数组,不破坏已有配置
#
# 注册两个 hook:
#   1. PreToolUse  + Write → block-self-generated-reports.sh
#      防止 Claude 用 Write 自造 report/channels(缺水印/hero-card/heatmap 直接 block)
#   2. PostToolUse + Write → post-channels-kb-ingest.sh
#      Write 完 channels-*-*.html 后自动跑 scripts/kb.py ingest,不依赖 SKILL.md 指示
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETTINGS=~/.claude/settings.json
PRE_HOOK="$REPO_ROOT/hooks/block-self-generated-reports.sh"
POST_HOOK="$REPO_ROOT/hooks/post-channels-kb-ingest.sh"

if ! command -v jq >/dev/null; then
    echo "[install] 需要 jq。macOS: brew install jq"
    exit 1
fi

# 确保 hook 可执行
chmod +x "$PRE_HOOK" "$POST_HOOK"

# 确保 settings.json 存在
mkdir -p ~/.claude
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"

# 备份
cp "$SETTINGS" "$SETTINGS.bak-$(date +%s)"

# 合并:把 Pre/Post hook 各自加到对应数组下,Write matcher 不重复
NEW=$(jq \
    --arg pre  "$PRE_HOOK" \
    --arg post "$POST_HOOK" '
    .hooks //= {} |

    # ---- PreToolUse / Write ----
    .hooks.PreToolUse //= [] |
    (.hooks.PreToolUse | map(select(.matcher == "Write")) | length) as $pre_exists |
    if $pre_exists == 0 then
        .hooks.PreToolUse += [{
            "matcher": "Write",
            "hooks": [{"type": "command", "command": $pre}]
        }]
    else
        .hooks.PreToolUse |= map(
            if .matcher == "Write" then
                .hooks |= (
                    if any(.[]; .command == $pre) then .
                    else . + [{"type": "command", "command": $pre}]
                    end
                )
            else . end
        )
    end |

    # ---- PostToolUse / Write ----
    .hooks.PostToolUse //= [] |
    (.hooks.PostToolUse | map(select(.matcher == "Write")) | length) as $post_exists |
    if $post_exists == 0 then
        .hooks.PostToolUse += [{
            "matcher": "Write",
            "hooks": [{"type": "command", "command": $post}]
        }]
    else
        .hooks.PostToolUse |= map(
            if .matcher == "Write" then
                .hooks |= (
                    if any(.[]; .command == $post) then .
                    else . + [{"type": "command", "command": $post}]
                    end
                )
            else . end
        )
    end
' "$SETTINGS")

echo "$NEW" > "$SETTINGS"

echo "[install] ✓ 两个 hook 已注册到 $SETTINGS"
echo "[install]   PreToolUse  Write → $PRE_HOOK"
echo "[install]   PostToolUse Write → $POST_HOOK"
echo "[install] 备份在 $SETTINGS.bak-*"
echo ""
echo "[install] 重启 Claude Code 让 settings 生效"
echo "[install] 卸载:编辑 $SETTINGS 删掉对应条目即可"
