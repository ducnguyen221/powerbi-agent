# powerbi-agent

MCP server + bộ skill giúp AI Agent làm việc **trực tiếp** với Power BI — kết nối
**Power BI Desktop (local)** & **Power BI Service (cloud)** vào trợ lý AI
(**Claude Code · Codex · Google Antigravity** và mọi MCP client). Thư mục này
**vừa là bản đang chạy, vừa là bộ cài** — copy nguyên thư mục sang máy khác là cài được.

> 👉 Hướng dẫn đầy đủ cho người dùng cuối: mở **`INSTALL.html`** bằng trình duyệt.
> 👉 Lộ trình tính năng (policy an toàn dữ liệu, report layer PBIR, template kit, pipeline 9 khâu): **[ROADMAP.md](ROADMAP.md)**.

## Cài / cập nhật (in-place)

Mở PowerShell **tại thư mục này** rồi chạy:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Trình cài làm tất cả tại chỗ: dựng `.venv`, cài deps, dò ADOMD.NET, đăng ký MCP vào 3 host
(trỏ về **chính thư mục này**), copy skill, kiểm thử. Chạy lại nhiều lần an toàn (idempotent).
Xong thì **khởi động lại** host.

| Tham số | Ý nghĩa |
|---|---|
| `-Hosts claude,codex,antigravity` | Chọn host (mặc định cả ba) |
| `-SkipVenv` | Chỉ cập nhật cấu hình host |
| `-SkipHosts` | Chỉ dựng venv, không sửa host |

## Mang sang máy mới

**Cách nhanh nhất — đóng gói sẵn:**

```powershell
powershell -ExecutionPolicy Bypass -File .\pack.ps1
```

→ tạo `powerbi-mcp-setup-<ngày>.zip` trên Desktop (đã tự loại `.venv`/`.env`/`.git`). Gửi file zip này đi.
Bên máy mới: giải nén vào `%USERPROFILE%\.mcp\powerbi-mcp` → chạy `install.ps1`.

**Hoặc copy tay:**

1. Copy **cả thư mục** này sang máy mới, **bỏ qua** `\.venv\` và `\.env\` (xem `.gitignore`).
   Nên đặt vào `%USERPROFILE%\.mcp\powerbi-mcp` để giống hệt cấu hình gốc.
2. Mở PowerShell tại đó, chạy `install.ps1`.
   - `.venv` được **dựng lại** tự động (nếu lỡ copy `.venv` cũ, trình cài phát hiện hỏng và rebuild).
   - Đường dẫn trong cấu hình host **suy từ vị trí thư mục** → không dính username máy gốc.
3. (Tùy chọn) Power BI Service: điền `TENANT_ID/CLIENT_ID/CLIENT_SECRET` vào `.env`.

## Nội dung thư mục

| File | Vai trò |
|---|---|
| `mcp_server_powerbi.py` | MCP server, 3 tool, ADOMD.NET đa-phiên-bản |
| `cli.py` | CLI gỡ rối thủ công (list / query / tables) — không bắt buộc cho MCP |
| `test_mcp_local.py` | Test nhanh kết nối local |
| `requirements.txt` | Deps pin chính xác (tái lập y hệt) |
| `requirements.loose.txt` | Deps "loose" — fallback khi pin cài lỗi |
| `.env.example` / `.env` | Mẫu / cấu hình cloud thật (`.env` **không** commit, **không** copy chia sẻ) |
| `install.ps1` / `uninstall.ps1` | Cài / gỡ in-place |
| `pack.ps1` | Đóng gói thành .zip sạch để mang đi (loại `.venv`/`.env`/`.git`) |
| `INSTALL.html` | Hướng dẫn cho người khác (tiếng Việt) |
| `skill/powerbi-mcp/SKILL.md` | Hướng dẫn agent dùng tool (cài cho cả 3 host) |
| `README_CLIENTS.md` | Tham khảo cấu hình host **thủ công** (machine-agnostic) |

## Chạy song song với `microsoft/powerbi-modeling-mcp` (khuyến nghị)

powerbi-agent **delegate phần modeling** cho MCP chính chủ của Microsoft và tập trung vào query/policy/report layer:

```bash
claude mcp add powerbi-modeling -s user -- npx -y "@microsoft/powerbi-modeling-mcp@latest" --start
```

| Việc | Server |
|---|---|
| Query DAX + policy an toàn dữ liệu, schema discovery, report layer PBIR (M2) | **powerbi-agent** (repo này) |
| Tạo/sửa measure/column/relationship, bulk ops, TMDL/PBIP, DAX validate | **powerbi-modeling** (Microsoft) |

## Bảo mật
- `.env` thật không bao giờ bị ghi đè, không nằm trong gói chia sẻ. Tool DAX mặc định **read-only**, cắt 1000 dòng.
- Policy `aggregate-only` (chặn `EVALUATE '<bảng>'` dump thô): bật bằng `POWERBI_AGGREGATE_ONLY=1` — M1 sẽ thành mặc định. Đây là guard chống rò rỉ sơ ý, không thay thế RLS.

## Gỡ cài
```powershell
.\uninstall.ps1              # gỡ khỏi host, giữ file + .venv + .env
.\uninstall.ps1 -RemoveVenv  # gỡ + xoá .venv
```
