# Cấu hình thủ công cho từng Host (tham khảo)

> **Khuyến nghị:** cứ chạy `install.ps1` (xem `README.md` / `INSTALL.html`) là tự đăng ký cả 3 host.
> File này chỉ để tham khảo khi bạn muốn **cấu hình tay** hoặc gỡ rối.

Thay `<DIR>` bằng đường dẫn tuyệt đối tới thư mục này trên máy của bạn
(khuyến nghị `%USERPROFILE%\.mcp\powerbi-mcp`). Dùng dấu gạch chéo xuôi `/` cho JSON/TOML.

- Python:  `<DIR>/.venv/Scripts/python.exe`
- Server:  `<DIR>/mcp_server_powerbi.py`

---

## 1. Claude Code

Cách an toàn nhất (không sửa tay file `.claude.json` lớn) — dùng CLI:

```powershell
claude mcp add powerbi-mcp-bridge -s user -e PYTHONUNBUFFERED=1 -- "<DIR>/.venv/Scripts/python.exe" -u "<DIR>/mcp_server_powerbi.py"
claude mcp list   # kiểm tra
```

## 2. Codex (OpenAI)

Thêm block vào `%USERPROFILE%\.codex\config.toml`:

```toml
[mcp_servers.powerbi-mcp-bridge]
command = "<DIR>/.venv/Scripts/python.exe"
args = ["-u", "<DIR>/mcp_server_powerbi.py"]
env = { PYTHONUNBUFFERED = "1" }
```

## 3. Google Antigravity

Thêm vào `mcpServers` trong `%USERPROFILE%\.gemini\antigravity\mcp_config.json`:

```json
{
  "mcpServers": {
    "powerbi-mcp-bridge": {
      "type": "stdio",
      "command": "<DIR>/.venv/Scripts/python.exe",
      "args": ["-u", "<DIR>/mcp_server_powerbi.py"],
      "env": { "PYTHONUNBUFFERED": "1" }
    }
  }
}
```

---

## Skill cho agent

Copy `skill/powerbi-mcp/SKILL.md` vào thư mục skill của host để agent biết quy trình dùng tool
(installer làm tự động):

- Claude Code: `%USERPROFILE%\.claude\skills\powerbi-mcp\SKILL.md`
- Codex: `%USERPROFILE%\.codex\skills\powerbi-mcp\SKILL.md`
- Antigravity: `%USERPROFILE%\.gemini\antigravity\skills\powerbi-mcp\SKILL.md`

Sau khi cấu hình, **khởi động lại** host để nạp MCP.
