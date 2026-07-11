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
- [x] Merge nhánh nâng cấp từ máy thứ hai (branch `tom-tools`, port vào package): TOM loader + `add_measure_local` + `add_relationship_local` (`tools_tom.py`, fallback — bulk/TMDL vẫn delegate modeling-mcp) + `distill_model_schema` (`tools_distill.py`, đổi tên từ `distill_report_model`; đích ghi mặc định `~/.powerbi-agent/distilled/` NGOÀI repo, cấu hình qua `POWERBI_DISTILL_DIR`).

### M1 — Policy + Discovery (an toàn dữ liệu)

| Feature | Chi tiết |
|---|---|
| `aggregate_only` mode (mặc định BẬT) | Chặn `EVALUATE '<bảng>'` / `EVALUATE ALL(...)` trần; cho `SUMMARIZECOLUMNS`/`GROUPBY`/`TOPN(n≤cap)`/`ROW`/truy vấn thuần measure; thông điệp từ chối kèm hướng dẫn viết lại |
| PII blocklist per-project (`policy.yaml`) | Cột cấm **project ra kết quả** (được dùng trong filter/measure — tính trên engine thì OK, kéo ra thì chặn) |
| Row caps phân biệt | Kết quả có cột dimension: mặc định 200 · thuần measure: không giới hạn thực tế |
| Audit log JSONL | timestamp · tool · DAX · số dòng · policy verdict — rà soát được |
| `list_tables()` / `describe_table(name)` | Schema discovery qua INFO/DMV — agent hết phải thuộc lòng `$SYSTEM.TBSCHEMA_*` |
| Token cache MSAL | Hết 1-round-trip-mỗi-call cho Service |

*Framing trung thực:* policy là guard chống rò rỉ **do sơ ý**, không phải bảo mật cứng —
bảo mật cứng = RLS trên model + service principal quyền tối thiểu. Có cờ `--unsafe-allow-raw` cho người chủ đích.

### M2 — Report layer (PBIR) + Template kit

| Feature | Chi tiết |
|---|---|
| `read_report_structure(pbip_path)` | Đọc pages/visuals/bookmarks từ PBIR |
| `add_report_page(pbip_path, kit, page_spec)` | Dựng trang mới bằng **clone-and-rebind**: copy block verbatim → thay đúng 4 thứ (name/position/queryState/visualType); giữ nguyên `visualContainerObjects` (style) |
| Guard cứng trong code | File phải ĐÓNG mới ghi · UTF-8 no-BOM · validate field tồn tại trong model trước khi bind · đăng ký `pages.json` |
| **Kit format v1** | `kit.yaml` (tokens) + `blueprint.md` (zone/visual/role→field) + `blocks/*.json` (verbatim mỗi loại visual) + `theme.json` + `preview.png` |
| Kit đầu tiên | `kpim-business-light` (canvas 1280×720, palette + panel + card refLabel + conditional formatting) |
| `list_templates()` | Liệt kê kit + preview cho người chọn |

### M3 — Distill + Pipeline skill

| Feature | Chi tiết |
|---|---|
| `distill_template(pbip_path, page, out_kit)` | Ngược của add_report_page: trang mẫu → kit (tách blocks verbatim + sinh blueprint.md) — nhân bản mẫu báo cáo thành tri thức tái dùng |
| `distill_model_schema(port, model_id)` | Model schema → Markdown + Mermaid ERD (đích ghi cấu hình được — KHÔNG mặc định vào repo) |
| Skill **`pbi-pipeline`** | Điều phối 9 khâu chuẩn: ①kết nối Power Query ②transform M (TMDL/PBIP-first) ③modeling+relationship (delegate MS) ④measure/calc column (delegate MS) ⑤DAX queries (policy-guarded) ⑥visual/matrix ⑦trang report ⑧nâng cao: page tooltip · drill-through · field parameters · what-if (bookmark: hướng dẫn thao tác tay) ⑨artifact: PLAN/CHANGESET/VERIFICATION/HANDOFF + doc phân tích per dự án |
| Vòng tri thức | Cuối dự án: bài học HOW → memory của agent; tri thức nghiệp vụ WHAT → knowledge base người dùng chỉ định |

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
