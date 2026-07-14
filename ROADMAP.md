# powerbi-agent — Kế hoạch triển khai (Implementation Roadmap)

> **powerbi-agent** = MCP server + bộ skill + template kit giúp AI Agent (Claude Code · Codex ·
> Antigravity · mọi MCP client) làm việc **trực tiếp và đúng chuẩn** với Power BI — từ Power Query
> đến trang báo cáo hoàn thiện — với chính sách an toàn dữ liệu enforce ở tầng server.
>
> Trạng thái: v0 (bridge read-only, đang chạy production) → v1.0 theo roadmap dưới đây.

---

## 1. Định vị & ranh giới

**Không xây lại modeling.** [`microsoft/powerbi-modeling-mcp`](https://github.com/microsoft/powerbi-modeling-mcp)
(official, MIT) đã phủ: tạo/sửa table, column, measure, relationship, bulk ops + transaction, TMDL/PBIP,
DAX validate. powerbi-agent **delegate** phần đó và tập trung vào 4 vùng Microsoft chưa/không làm:

| Vùng | Vì sao là khoảng trống |
|---|---|
| **Report layer (PBIR)** — tạo/sửa trang báo cáo, visual | modeling-mcp tuyên bố rõ *không* sửa report pages |
| **Data-safety policy** — chặn dump dữ liệu thô vào context LLM | Chưa server nào enforce; các server hiện tại trả raw rows |
| **Template kit** — dựng báo cáo từ mẫu chuẩn hóa, distill mẫu thành kit | Layout agent tự sinh luôn xấu; clone-and-rebind đã chứng minh |
| **Pipeline 9 khâu** — quy trình chuẩn end-to-end cho agent + artifact | Các server chỉ đưa tool rời, không đưa quy trình |

**Kiến trúc 4 tầng:**

```
T4  WORKFLOW & KNOWLEDGE   skill pbi-pipeline · template kits · distill · artifacts
T3  POLICY                 aggregate-only · PII blocklist · audit log · row caps
T2  MCP TOOLS (repo này)   query · schema discovery · PBIR read/write · template · TOM fallback
T1  DELEGATE               microsoft/powerbi-modeling-mcp (modeling, bulk, TMDL, DAX validate)
```

## 2. Khả năng tích hợp (integration matrix)

| Đích kết nối | Giao thức | Trạng thái |
|---|---|---|
| **Power BI Desktop** (file .pbix/.pbip đang mở) | ADOMD.NET → `localhost:<port>` (tự dò port msmdsrv) | ✅ v0 |
| **Power BI Service / Fabric** (dataset đã publish) | REST `executeQueries` + MSAL service principal | ✅ v0 |
| **PBIP project files** (file đóng, git-versioned) | Đọc/ghi trực tiếp TMDL (model) + PBIR JSON (report) | 🔜 v1 |
| **MCP host** | stdio — Claude Code, Codex CLI, Antigravity, VS Code, Cursor… | ✅ v0 (installer 3 host, mở rộng được) |
| **microsoft/powerbi-modeling-mcp** | Chạy song song, phân vai qua skill (không trùng tool name) | 🔜 M0 |

Yêu cầu hệ: Windows (Power BI Desktop chỉ có trên Windows) · Python 3.11+ · ADOMD.NET
(SSMS 18–22 / standalone / GAC — tự dò, override `ADOMD_LIB_DIR`).

## 3. Feature spec theo milestone

### v0 — hiện có (production)

| Tool | Mô tả |
|---|---|
| `list_local_reports()` | Liệt kê báo cáo Desktop đang mở (port + model ID) |
| `execute_dax_local(port, model_id, dax, max_rows)` | Chạy DAX lên Desktop |
| `execute_dax_service(dataset_id, dax, max_rows)` | Chạy DAX lên Service |

Kèm: installer in-place 3 host (`install.ps1`), CLI debug (`cli.py`), skill mô tả cách dùng.

### M0 — Nền sản phẩm

- [x] Tách `mcp_server_powerbi.py` → package `powerbi_agent/` (util · adomd · discovery · tools_query · policy · app); `mcp_server_powerbi.py` giữ làm shim back-compat — host config KHÔNG phải đổi.
- [x] `pyproject.toml` v0.1.0 + entry `powerbi-agent`; `requirements.txt` giữ cho installer.
- [x] Test suite pytest (19 unit: util/adomd-probe/policy/back-compat) + GitHub Actions (windows runner, ruff + pytest, marker `integration` skip trên CI).
- [x] Policy khung sẵn từ M0: `POWERBI_AGGREGATE_ONLY=1` bật chặn dump thô (mặc định tắt — M1 đảo mặc định + PII blocklist + audit).
- [x] Cài `microsoft/powerbi-modeling-mcp` song song (✔ Connected); doc phân vai trong README + SKILL.md.
- [x] Hợp nhất nhánh đóng góp single-file vào package: TOM loader + `add_measure_local` + `add_relationship_local` (`tools_tom.py`, fallback — bulk/TMDL vẫn delegate modeling-mcp) + `distill_model_schema` (`tools_distill.py`, đổi tên từ `distill_report_model`; đích ghi mặc định `~/.powerbi-agent/distilled/` NGOÀI repo, cấu hình qua `POWERBI_DISTILL_DIR`).

### M1 — Policy + Discovery (an toàn dữ liệu) — ✅ XONG 2026-07-12

- [x] `aggregate_only` mặc định BẬT (opt-out `POWERBI_AGGREGATE_ONLY=0`); chặn kèm hint viết lại.
- [x] PII blocklist qua `policy.json` (gitignored; mẫu `policy.example.json`; env `POWERBI_POLICY_FILE`). Heuristic bảo thủ: chặn khi cột xuất hiện bất kỳ đâu trong DAX (tài liệu hóa rõ).
- [x] Row cap dimension 200 (`POWERBI_DIMENSION_ROW_CAP`); thuần measure không siết.
- [x] Audit log JSONL `~/.powerbi-agent/audit/YYYY-MM.jsonl` (ts·tool·verdict·rows·dax) — lỗi ghi audit không phá truy vấn.
- [x] `list_tables` / `describe_table` (DMV; đã sửa bug `[ExplicitDataType]` + lọc `RowNumber-*` + TOM enum map — phát hiện qua UAT live).
- [x] Token cache MSAL (app singleton).

### M2 — Report layer (PBIR) + Template kit — ✅ XONG 2026-07-12

- [x] `pbir.py`: resolve .pbip/.Report/definition · find_page (GUID/displayName) · projection/rebind (bỏ `sortDefinition` cũ) · set_title giữ style · GUID 20-hex · UTF-8 no-BOM · deep_sanitize (walk toàn cây: queryState + objects + conditional color + textbox text + filterConfig).
- [x] `apply_template(report_path, kit_dir, page_spec)` — clone-and-rebind thành code; đăng ký pages.json; bỏ parentGroupName/expansionStates; cảnh báo file-đóng trong output.
- [x] `distill_template(report_path, page, out_dir, sanitize)` — trang → kit (1 block giàu style nhất/loại + blueprint 100% visual + _page.json + kit.json).
- [x] Kit format v1 = `kit.json` + `blueprint.md` + `blocks/*.json` + `_page.json` (JSON thay YAML — zero dep; preview.png để sau).
- [x] Kit đầu tiên `templates/kpim-business-light` — distill từ trang chuẩn thật 30 visual, 12 loại block (card refLabel + conditional color, combo chart, pivot, slicer, map…), ĐÃ sanitize.
- [x] `list_templates()` (repo templates/ + env `POWERBI_TEMPLATES_DIR`).
- Dời sau: `read_report_structure` (blueprint của distill đã cover nhu cầu đọc), validate field-tồn-tại-trong-model trước khi bind (làm được qua describe_table thủ công trong pipeline).

### M3 — Distill + Pipeline skill — ✅ XONG 2026-07-12

- [x] `distill_model_schema` (đích ghi `POWERBI_DISTILL_DIR`/`~/.powerbi-agent/distilled/`) — live PASS trên model 10 bảng/174 measure + Mermaid ERD.
- [x] Skill **`pbi-pipeline`** 9 khâu (điều phối 2 MCP, cổng kiểm mỗi khâu, 4 artifact, bookmark-để-tay, hỏi PII đầu dự án) — cài cả 3 host, install.ps1 copy mọi skill.
- [x] Vòng tri thức: distill_model_schema (model→blueprint) + distill_template (trang đẹp→kit) + bài học→memory.

**UAT (docs/UAT-REPORT.md):** 17 ca PASS trên dashboard thật (.pbip 7 trang + model 174 measure + Desktop live) — 4 defect tìm thấy & sửa trong UAT (deep-sanitize leak, sortDefinition leak, DMV ExplicitDataType, TOM enum map).

### M4 — Sản phẩm hóa

- [ ] Docs song ngữ (README EN + VI) · demo GIF/video · ví dụ end-to-end (CSV → model → 2 trang báo cáo theo kit).
- [ ] Versioned release + CHANGELOG.
- [ ] (Cân nhắc) Đăng MCP registry/marketplace cộng đồng.

## 4. Definition of Done (v1.0)

1 dự án mẫu chạy trọn 9 khâu: từ CSV nguồn → `.pbip` có model + measures + 2 trang báo cáo
theo kit + tooltip/drill-through — agent tự chạy qua skill `pbi-pipeline`, **không một dòng dữ liệu
thô nào vào context** (audit log chứng minh), đủ 4 artifact bàn giao.

## 5. Rủi ro đã nhận diện

| Rủi ro | Đối sách |
|---|---|
| modeling-mcp đang Public Preview, API đổi trước GA | Pin version; theo dõi release notes |
| 2 MCP server cùng ghi 1 model | Quy ước trong skill: không interleave write; modeling ops nhường MS server |
| PBIR schema đổi theo Desktop release | Kit lưu schema version; validate khi apply |
| Policy DAX guard là best-effort parse | Tuyên bố rõ giới hạn; RLS mới là bảo mật cứng |
| Bookmark clone dễ vỡ báo cáo | Không tự động hóa bookmark — hướng dẫn thao tác tay |
