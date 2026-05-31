#!/usr/bin/env bash
# 安装 GEOVisibilityTool hooks 到 ~/.claude/settings.json
# 用 jq 合并 PreToolUse 数组,不破坏已有配置
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETTINGS=~/.claude/settings.json
HOOK_PATH="$REPO_ROOT/hooks/block-self-generated-reports.sh"

if ! command -v jq >/dev/null; then
    echo "[install] 需要 jq。macOS: brew install jq"
    exit 1
fi

# 确保 hook 可执行
chmod +x "$HOOK_PATH"

# 确保 settings.json 存在
mkdir -p ~/.claude
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"

# 备份
cp "$SETTINGS" "$SETTINGS.bak-$(date +%s)"

# 合并:把我们的 hook 加到 PreToolUse Write matcher 下,不重复
NEW=$(jq --arg cmd "$HOOK_PATH" '
    .hooks //= {} |
    .hooks.PreToolUse //= [] |
    # 找到 matcher=Write 的项
    (.hooks.PreToolUse | map(select(.matcher == "Write")) | length) as $existing |
    if $existing == 0 then
        .hooks.PreToolUse += [{
            "matcher": "Write",
            "hooks": [{"type": "command", "command": $cmd}]
        }]
    else
        # 已有 Write matcher,追加我们的 command(去重)
        .hooks.PreToolUse |= map(
            if .matcher == "Write" then
                .hooks |= (
                    if any(.[]; .command == $cmd) then .
                    else . + [{"type": "command", "command": $cmd}]
                    end
                )
            else . end
        )
    end
' "$SETTINGS")

echo "$NEW" > "$SETTINGS"

echo "[install] ✓ hook 已注册到 $SETTINGS"
echo "[install] hook 路径:$HOOK_PATH"
echo "[install] 备份在 $SETTINGS.bak-*"
echo ""
echo "[install] 重启 Claude Code 让 settings 生效"
echo "[install] 卸载:编辑 $SETTINGS 删掉对应条目即可"
