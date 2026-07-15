# plugins/ — Plugin pack (nguồn DUY NHẤT của skills)

`powerbi-agent/` là plugin theo chuẩn Claude/Codex marketplace:

- `powerbi-agent/.claude-plugin/plugin.json` — **manifest của plugin** (tên, version, skills ở đâu).
  ≠ `/.claude-plugin/marketplace.json` ở gốc repo (= **danh mục chợ**, khai báo repo này phân phối
  plugin nào). Hai file này là 2 tầng của cùng một hệ thống — KHÔNG trùng lặp, thiếu 1 là hỏng
  flow `claude plugin marketplace add` → `plugin install`.
- `powerbi-agent/skills/` — 4 skill dùng chung mọi host. **Sửa skill Ở ĐÂY** — installer copy
  đi `~/.claude/skills/`, `~/.codex/skills/`, `~/.gemini/antigravity/skills/`; đừng sửa bản copy.

Chi tiết từng skill: xem bảng INDEX trong [`../README.md`](../README.md) và luật làm việc
trong [`../AGENTS.md`](../AGENTS.md).

## Plugin này chạy trên host nào?

| Host | Cách hiện dạng plugin | Lệnh |
|---|---|---|
| **Claude Code** | Trình quản lý plugin của app | `claude plugin marketplace add ducnguyen221/powerbi-agent` → `claude plugin install powerbi-agent@powerbi-agent` |
| **Codex CLI** | `codex plugin list` (đọc CÙNG `marketplace.json`) | `codex plugin marketplace add ...` → `codex plugin add powerbi-agent@powerbi-agent` |
| **Antigravity** | Không có store → skill nạp từ `~/.gemini/antigravity/skills/` (installer copy) | `install.ps1 -Hosts antigravity` |

Đã verify: cùng 1 `.claude-plugin/marketplace.json` cài sạch trên cả Claude lẫn Codex; commands/agents được auto-discover (KHÔNG khai báo trong plugin.json — Claude từ chối field `agents`).
