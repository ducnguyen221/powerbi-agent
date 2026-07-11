# powerbi-agent

**MCP server + bộ skill biến AI Agent thành chuyên gia phân tích làm việc TRỰC TIẾP trên Power BI** —
từ truy vấn DAX có chính sách an toàn dữ liệu, đến dựng trang báo cáo đẹp theo template,
đến quy trình phân tích end-to-end 9 khâu.

Hỗ trợ **Power BI Desktop (local)** · **Power BI Service (cloud)** · **PBIP/PBIR (project files)**.
Host: **Claude Code · Codex CLI · Google Antigravity** và mọi MCP client stdio.

> 📘 Cài đặt chi tiết từng bước (có hình): mở **`INSTALL.html`** · Lộ trình: **[ROADMAP.md](ROADMAP.md)** · Kết quả UAT: **[docs/UAT-REPORT.md](docs/UAT-REPORT.md)**

## Cài bằng AI Agent (khuyến nghị — 1 câu lệnh)

Dán vào agent của bạn (Claude Code / Codex / Antigravity):

```
Clone https://github.com/ducnguyen221/powerbi-agent vào ~/.mcp/powerbi-mcp rồi chạy install.ps1 trong đó (đọc script trước khi chạy), sau đó restart MCP host.
```

Agent sẽ: clone → dựng `.venv` → dò ADOMD.NET/TOM (mọi bản SSMS/standalone/GAC) → đăng ký MCP
vào cả 3 host → copy 2 skill (`powerbi-mcp`, `pbi-pipeline`). Cài tay: xem `INSTALL.html`.

```powershell
git clone https://github.com/ducnguyen221/powerbi-agent "$env:USERPROFILE\.mcp\powerbi-mcp"
cd "$env:USERPROFILE\.mcp\powerbi-mcp"
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Yêu cầu: Windows (Power BI Desktop chỉ có trên Windows) · Python 3.11+ · ADOMD.NET
(có sẵn nếu cài SSMS; hoặc [Analysis Services client libraries](https://learn.microsoft.com/en-us/analysis-services/client-libraries)).

## 11 tool

| Nhóm | Tool | Chức năng |
|---|---|---|
| **Khám phá** | `list_local_reports` | Báo cáo Desktop đang mở (port + model ID) |
| | `list_tables` | Bảng trong model (lọc bảng hệ thống) |
| | `describe_table` | Cột + kiểu dữ liệu + measure của 1 bảng |
| **Truy vấn** 🛡️ | `execute_dax_local` | DAX lên Desktop — qua policy an toàn dữ liệu |
| | `execute_dax_service` | DAX lên Service (MSAL, token cache) — qua policy |
| **Ghi model** | `add_measure_local` | Tạo/sửa measure qua TOM |
| | `add_relationship_local` | Tạo relationship Many-to-One qua TOM |
| **Template** 🎨 | `list_templates` | Kit báo cáo có sẵn |
| | `apply_template` | Dựng TRANG MỚI từ kit — clone-and-rebind, style giữ nguyên |
| | `distill_template` | Chưng cất trang đẹp thành kit tái dùng (sanitize được) |
| **Tri thức** | `distill_model_schema` | Model → Markdown blueprint + Mermaid ERD |

## 🛡️ Chính sách an toàn dữ liệu (enforce ở server, không phải lời nhắc)

Nguyên tắc: **dữ liệu thô ở lại trong engine Power BI — chỉ kết quả tổng hợp vào context LLM.**

- **aggregate-only (mặc định BẬT):** `EVALUATE 'Bảng'` / `EVALUATE ALL(...)` bị từ chối kèm hướng
  dẫn viết lại bằng `SUMMARIZECOLUMNS`/`TOPN`/measure. Tắt: `POWERBI_AGGREGATE_ONLY=0`.
- **PII blocklist:** copy `policy.example.json` → `policy.json`, liệt kê cột cấm project
  (SĐT, CMND, email…). Cột bị chặn ở MỌI truy vấn.
- **Audit log:** mọi truy vấn ghi `~/.powerbi-agent/audit/*.jsonl` (verdict + số dòng) —
  bằng chứng kiểm toán "không dump dữ liệu thô".
- **Trần dimension:** kết quả có cột chữ bị siết 200 dòng (thuần measure không giới hạn).
- *Trung thực về giới hạn:* đây là guard chống rò rỉ **sơ ý** — bảo mật cứng vẫn là RLS trên
  model + service principal quyền tối thiểu.

## 🎨 Template kit — báo cáo đẹp tái tạo được

Bài học đắt giá: **layout agent tự dựng từ đầu luôn xấu; clone trang đã chứng minh + đổi binding thì đẹp.**
`apply_template` biến luật đó thành code: giữ nguyên `visualContainerObjects` (style), chỉ đổi
name/position/fields/visualType/title.

Kit = thư mục text git-được:

```
templates/kpim-business-light/     # kit mẫu đi kèm (đã sanitize)
  kit.json          # meta: canvas, blocks, roles
  blueprint.md      # bản đồ trang mẫu: 30 visual, vị trí, binding
  blocks/*.json     # visual.json VERBATIM mỗi loại (card KPI, combo chart, pivot, slicer, map…)
  _page.json        # page settings + nền
```

Vòng tri thức: trang nào user khen đẹp → `distill_template` thành kit → dự án sau `apply_template` tái tạo.
Kit chứa binding nghiệp vụ thật thì để NGOÀI repo (env `POWERBI_TEMPLATES_DIR`); muốn chia sẻ → `sanitize=True`.

## 🤝 Chạy song song microsoft/powerbi-modeling-mcp (khuyến nghị)

powerbi-agent **không xây lại modeling** — delegate cho MCP chính chủ Microsoft:

```bash
claude mcp add powerbi-modeling -s user -- npx -y "@microsoft/powerbi-modeling-mcp@latest" --start
```

| Việc | Server |
|---|---|
| Query DAX + policy, schema discovery, template/PBIR report layer, distill | **powerbi-agent** |
| Tạo/sửa table/column/measure/relationship, bulk + transaction, TMDL, DAX validate | **powerbi-modeling** (Microsoft) |

## 📐 Quy trình 9 khâu (skill `pbi-pipeline`)

Agent làm dự án Power BI trọn gói theo thứ tự chuẩn, mỗi khâu có cổng kiểm:

1. Kết nối dữ liệu (Power Query, M parameter) → 2. Transform M (kiểu dữ liệu tường minh)
→ 3. Mô hình hóa star schema + relationship → 4. Measure/calc column DAX (verify từng cái)
→ 5. Truy vấn tổng hợp (policy gác) → 6+7. Visual & trang báo cáo từ template
→ 8. Nâng cao (tooltip, drill-through, parameters; bookmark để tay) → 9. Artifact + chưng cất tri thức.

Chi tiết: `skill/pbi-pipeline/SKILL.md` (tự cài vào host khi chạy install.ps1).

## Cấu trúc repo

```
powerbi_agent/          # package server (query, tom, template, distill, policy, pbir)
mcp_server_powerbi.py   # entrypoint back-compat (host đăng ký file này)
skill/                  # 2 skill: powerbi-mcp (tool guide) + pbi-pipeline (quy trình 9 khâu)
templates/              # kit mẫu kpim-business-light (sanitized)
tests/                  # 32 unit tests (CI windows-latest)
install.ps1             # cài in-place 3 host, idempotent
policy.example.json     # mẫu PII blocklist
docs/UAT-REPORT.md      # kết quả UAT trên dashboard thật
```

## Bảo mật & vận hành

- `.env` (service principal cloud) không bao giờ bị ghi đè/commit — chỉ tạo từ `.env.example`.
- Tool GHI model nhắc rõ trong docstring; ghi REPORT chỉ khi file .pbip đóng (tool tự cảnh báo).
- Gỡ: `.\uninstall.ps1` (giữ file) · `.\uninstall.ps1 -RemoveVenv`.

## License

MIT — © 2026 Duc Nguyen ([ducnguyen221](https://github.com/ducnguyen221))
