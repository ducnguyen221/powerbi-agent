# plugins/ — Plugin pack (nguồn DUY NHẤT của skills)

`powerbi-agent/` là plugin theo chuẩn Claude/Codex marketplace:

- `powerbi-agent/.claude-plugin/plugin.json` — **manifest của plugin** (tên, version, skills ở đâu).
  ≠ `/.claude-plugin/marketplace.json` ở gốc repo (= **danh mục chợ**, khai báo repo này phân phối
  plugin nào). Hai file này là 2 tầng của cùng một hệ thống — KHÔNG trùng lặp, thiếu 1 là hỏng
  flow `claude plugin marketplace add` → `plugin install`.
- `powerbi-agent/skills/` — 3 skill dùng chung mọi host. **Sửa skill Ở ĐÂY** — installer copy
  đi `~/.claude/skills/`, `~/.codex/skills/`, `~/.gemini/antigravity/skills/`; đừng sửa bản copy.

Chi tiết từng skill: xem bảng INDEX trong [`../README.md`](../README.md) và luật làm việc
trong [`../AGENTS.md`](../AGENTS.md).
