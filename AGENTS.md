# AGENTS.md — powerbi-agent

> File hướng dẫn CHUẨN cho mọi AI agent (Claude Code · Codex CLI · Google Antigravity · bất kỳ
> tool nào đọc AGENTS.md). `CLAUDE.md` và `GEMINI.md` chỉ là con trỏ về file này — sửa Ở ĐÂY.

## 1. Repo này là gì

**powerbi-agent** = MCP server (11 tool) + 3 skill giúp AI Agent làm phân tích dữ liệu
**end-to-end trên Power BI**: truy vấn DAX qua chính sách an toàn dữ liệu, khám phá/ghi model,
dựng trang báo cáo theo template kit, và quy trình dự án chuẩn hóa.

```
powerbi_agent/                  # package MCP server (Python) — query · policy · TOM · PBIR · distill
mcp_server_powerbi.py           # entrypoint host đăng ký (shim — ĐỪNG đổi tên/di chuyển)
plugins/powerbi-agent/skills/   # 3 skill dùng chung mọi host (nguồn DUY NHẤT — sửa ở đây)
  kpim-analysis/                #   pha NGHIỆP VỤ: khảo sát → tài liệu hóa → kế hoạch
  pbi-pipeline/                 #   pha KỸ THUẬT: 9 khâu Power Query → model → DAX → report
  powerbi-mcp/                  #   hướng dẫn dùng 11 tool + luật an toàn dữ liệu
.claude-plugin/marketplace.json # cài skills dạng plugin (Claude/Codex)
hosts/{claude,codex,antigravity}/  # hướng dẫn đăng ký RIÊNG từng host
templates/                      # template kit báo cáo (kit.json + blocks/*.json verbatim)
install.ps1                     # cài in-place: venv + dò ADOMD/TOM + đăng ký CẢ 3 host + copy skill
tests/ · .github/workflows/     # pytest + ruff, CI windows-latest
```

## 2. Cài đặt (agent thực hiện được toàn bộ)

```powershell
git clone https://github.com/ducnguyen221/powerbi-agent "$env:USERPROFILE\.mcp\powerbi-mcp"
cd "$env:USERPROFILE\.mcp\powerbi-mcp"
powershell -ExecutionPolicy Bypass -File .\install.ps1   # venv + ADOMD + đăng ký 3 host + skill
```

- Sau cài: **restart MCP host** rồi verify (`claude mcp list` → `powerbi-mcp-bridge ✔ Connected`).
- Chỉ cần SKILLS (không MCP): `claude plugin marketplace add ducnguyen221/powerbi-agent`
  → `claude plugin install powerbi-agent@powerbi-agent` (Codex tương tự). Lưu ý: plugin
  KHÔNG dựng venv/MCP — đầy đủ phải chạy `install.ps1`.
- Khuyến nghị cài kèm modeling chính chủ Microsoft:
  `claude mcp add powerbi-modeling -s user -- npx -y "@microsoft/powerbi-modeling-mcp@latest" --start`
- Chi tiết từng host: `hosts/<tên host>/README.md`.

## 3. Cách agent làm việc với Power BI (luật CỨNG)

1. **Thứ tự skill:** dự án mới → `kpim-analysis` (nghiệp vụ) → `pbi-pipeline` (9 khâu kỹ thuật);
   câu hỏi lẻ → tool trực tiếp theo `powerbi-mcp`.
2. **Dữ liệu thô ở lại engine** — policy aggregate-only đang enforce ở server: viết DAX tổng hợp
   (SUMMARIZECOLUMNS/TOPN/measure), KHÔNG `EVALUATE 'Bảng'`. Đầu dự án hỏi user cột PII → ghi
   `policy.json`.
3. **PBIP-first** — bảo user Save As `.pbip` ngay đầu dự án (model = TMDL, report = PBIR, git được).
4. **Ghi model lúc nào cũng được (engine live); ghi REPORT chỉ khi file .pbip ĐÓNG** — mở +
   Ctrl+S phiên cũ sẽ đè mất trang agent vừa tạo.
5. **Không bao giờ tự dựng layout trang từ đầu** — `list_templates` → `apply_template`
   (clone-and-rebind). Trang đẹp user duyệt → `distill_template` thành kit.
6. **Mỗi khâu có cổng kiểm chạy được** — không verify = chưa xong. Nghiệm thu MẮT trang báo cáo
   là của user (agent không thấy render).
7. **Phân vai 2 MCP:** modeling hàng loạt/TMDL/validate → `powerbi-modeling` (Microsoft);
   query + policy + report layer + distill → `powerbi-agent` (repo này).

## 4. Điều phối NHIỀU agent cùng lúc (multi-agent)

Repo này thiết kế để Claude Code + Codex + Antigravity làm việc **song song trên cùng 1 dự án
Power BI**. Luật phối hợp:

### 4.1 Single-writer — quy tắc số 1
- **MODEL** (measure/relationship/TOM/TMDL): tại một thời điểm chỉ **1 agent GHI**. Ghi xong
  (SaveChanges) mới bàn giao. Không interleave write giữa 2 MCP server hoặc 2 agent.
- **REPORT** (`*.Report/` PBIR): 1 agent **sở hữu trọn** thư mục này trong 1 lượt làm việc,
  và chỉ khi file .pbip đóng.
- **Lock convention** (tool-agnostic): trước khi GHI model/report, tạo file
  `<thư mục dự án>/.pbi-write-lock` nội dung `<tên agent> | <việc> | <timestamp>`; xóa khi xong.
  Agent khác thấy lock → CHỈ ĐỌC (query/analyze), không ghi, không xóa lock của agent khác.

### 4.2 Phân vai gợi ý (điều chỉnh theo dự án)
| Vai | Agent gợi ý | Làm gì |
|---|---|---|
| **Orchestrator / Builder** | Claude Code | Chạy kpim-analysis + pbi-pipeline, GHI model & report, giữ lock |
| **Reviewer / Second-opinion** | Codex | CHỈ ĐỌC: verify measure (`execute_dax_local` đối chiếu số), soi ERD từ `distill_model_schema`, review DAX/page_spec trước khi Builder ghi |
| **Analyst / Documenter** | Antigravity | Pha kpim-analysis (tài liệu nghiệp vụ, mindmap, kế hoạch), soạn `page_spec` JSON, viết artifact bàn giao |

Mọi vai đều đọc được an toàn đồng thời — tool ĐỌC (list/describe/execute_dax/distill) không cần lock.

### 4.3 Kênh giao tiếp chung giữa các agent
- **Artifact files trong thư mục dự án** (nguồn sự thật, agent nào cũng đọc/ghi nối tiếp):
  `PLAN.md` → `CHANGESET.md` → `VERIFICATION.md` → `HANDOFF.md` (+ tài liệu kpim-analysis).
  Bàn giao giữa 2 agent = ghi rõ trạng thái vào artifact, KHÔNG dựa vào trí nhớ phiên chat.
- **Audit log** `~/.powerbi-agent/audit/*.jsonl` = sổ cái chung mọi truy vấn (agent nào, chặn gì)
  — Reviewer dùng làm bằng chứng kiểm tra.
- **Blueprint từ `distill_model_schema`** = "bản đồ model" chung: Builder tạo sau mỗi đợt ghi
  model; các agent khác đọc thay vì tự query lại schema.

### 4.4 Checklist khi nhận bàn giao (agent nào cũng vậy)
1. Đọc `AGENTS.md` này + artifact mới nhất trong thư mục dự án.
2. `list_local_reports` xác nhận trạng thái Desktop; kiểm tra `.pbi-write-lock`.
3. Làm phần việc của vai mình; cập nhật artifact; xóa lock nếu mình tạo.

## 5. Quy ước phát triển repo (khi agent sửa CODE repo này)

- Python 3.11+, ruff (line 120), pytest — chạy `pytest tests -m "not integration"` + ruff trước commit.
- `mcp_server_powerbi.py` là shim back-compat: host đăng ký file này — GIỮ bề mặt import.
- Skill là nguồn duy nhất ở `plugins/powerbi-agent/skills/` — installer copy đi các host,
  ĐỪNG sửa bản copy trong `~/.claude/skills/...`.
- `.ps1` phải UTF-8 **có BOM** (PowerShell 5.1 + tiếng Việt); JSON PBIR ghi UTF-8 **không BOM**.
- KHÔNG commit: `.env`, `policy.json`, `.venv/`, kit chứa binding nghiệp vụ thật (sanitize trước),
  schema model khách (distill ghi ra NGOÀI repo), tham chiếu máy cá nhân.
- Docs công khai (README/INSTALL/docs/) phải machine-agnostic — không đường dẫn/tên máy riêng.

## 6. File nào host nào đọc

| Host | File hướng dẫn | Skills | MCP config |
|---|---|---|---|
| Claude Code | `CLAUDE.md` → trỏ về đây | `~/.claude/skills/` (installer copy) hoặc plugin | `~/.claude.json` |
| Codex CLI | `AGENTS.md` (file này, native) | `~/.codex/skills/` hoặc plugin | `~/.codex/config.toml` |
| Antigravity | `GEMINI.md` → trỏ về đây | `~/.gemini/antigravity/skills/` | `~/.gemini/antigravity/mcp_config.json` |
