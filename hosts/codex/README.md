# Codex CLI — cài & đăng ký powerbi-agent

Codex đọc **`AGENTS.md`** ở gốc repo một cách native — mọi luật làm việc nằm ở đó.

## Cách 1 — Trọn bộ (MCP + venv + skills) — khuyến nghị

```powershell
git clone https://github.com/ducnguyen221/powerbi-agent "$env:USERPROFILE\.mcp\powerbi-mcp"
cd "$env:USERPROFILE\.mcp\powerbi-mcp"
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Hosts codex
```

Installer thêm block `[mcp_servers.powerbi-mcp-bridge]` vào `~/.codex/config.toml`
(backup `.bak`) và copy 3 skill vào `~/.codex/skills/`. **Restart phiên Codex** sau cài.

Đăng ký tay (nếu muốn tự làm):

```toml
# ~/.codex/config.toml
[mcp_servers.powerbi-mcp-bridge]
command = "C:/Users/<you>/.mcp/powerbi-mcp/.venv/Scripts/python.exe"
args    = ["C:/Users/<you>/.mcp/powerbi-mcp/mcp_server_powerbi.py"]
env     = { PYTHONUNBUFFERED = "1" }
```

## Cách 2 — Chỉ skills (dạng plugin marketplace git)

```bash
codex plugin marketplace add https://github.com/ducnguyen221/powerbi-agent
codex plugin add powerbi-agent@powerbi-agent
```

## Khuyến nghị kèm theo

Đăng ký thêm `powerbi-modeling` (Microsoft) cho modeling ops — xem [`AGENTS.md`](../../AGENTS.md) §2.
Vai gợi ý cho Codex trong tổ đa-agent: **Reviewer/second-opinion** (chỉ đọc) — §4.2.
