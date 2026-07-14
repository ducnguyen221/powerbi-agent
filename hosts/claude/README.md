# Claude Code — cài & đăng ký powerbi-agent

## Cách 1 — Trọn bộ (MCP + venv + skills) — khuyến nghị

```powershell
git clone https://github.com/ducnguyen221/powerbi-agent "$env:USERPROFILE\.mcp\powerbi-mcp"
cd "$env:USERPROFILE\.mcp\powerbi-mcp"
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Hosts claude
```

Installer merge server `powerbi-mcp-bridge` vào `~/.claude.json` (user scope, backup `.bak`,
không đụng server khác) và copy 3 skill vào `~/.claude/skills/`. **Restart Claude Code** sau cài.

Verify: `claude mcp list` → `powerbi-mcp-bridge … ✔ Connected`.

## Cách 2 — Chỉ skills (dạng plugin, không MCP)

```bash
claude plugin marketplace add ducnguyen221/powerbi-agent
claude plugin install powerbi-agent@powerbi-agent
```

Dùng khi chỉ cần quy trình/kiến thức (kpim-analysis, pbi-pipeline) mà chưa cần tool DAX.
Muốn tool → quay lại Cách 1.

## Khuyến nghị kèm theo

```bash
claude mcp add powerbi-modeling -s user -- npx -y "@microsoft/powerbi-modeling-mcp@latest" --start
```

Phân vai 2 server + luật multi-agent: xem [`AGENTS.md`](../../AGENTS.md) §3–§4.
