# Claude Code Hooks Integration

## セットアップ

### 1. シェルエイリアス（セッション開始を自動化）

`~/.zshrc` または `~/.bashrc` に追加:

```bash
# Claude Code with auto session logging
claude-session() {
    # Start session
    python ~/workspace/obsidian_vault/docs/03_project/00_thedomainai/cli-session-log/hooks/claude_session_hook.py start "$1"

    # Run Claude Code
    claude "$@"

    # End session
    python ~/workspace/obsidian_vault/docs/03_project/00_thedomainai/cli-session-log/hooks/claude_session_hook.py stop
}

alias cs='claude-session'
```

### 2. Claude Code Settings（セッション終了を自動化）

`~/.claude/settings.json` に追加:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python ~/workspace/obsidian_vault/docs/03_project/00_thedomainai/cli-session-log/hooks/claude_session_hook.py stop"
          }
        ]
      }
    ]
  }
}
```

## 使い方

### 自動セッション管理

```bash
# エイリアスを使用（推奨）
cs "今日のタスク"

# セッションが自動で開始・終了される
```

### 手動操作

```bash
# セッション開始
python hooks/claude_session_hook.py start "セッション名"

# 現在のセッション確認
python hooks/claude_session_hook.py current

# ログ追加
python hooks/claude_session_hook.py log User "質問内容"
python hooks/claude_session_hook.py log AI "回答内容"

# セッション終了
python hooks/claude_session_hook.py stop
```

## 保存先

セッションは以下に保存されます:
```
~/workspace/obsidian_vault/docs/01_resource/sessions/YYYY-MM/session-XXXXXXXX.md
```
