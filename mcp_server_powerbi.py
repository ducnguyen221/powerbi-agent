"""Entrypoint back-compat — 3 host (Claude/Codex/Antigravity) đăng ký file này.

Từ v0.1.0 code thật nằm trong package `powerbi_agent/` (xem ROADMAP.md §M0).
File này chỉ re-export để: (1) host config KHÔNG phải đổi, (2) cli.py /
test_mcp_local.py import như cũ.
"""

import os
import sys

# Đảm bảo package tìm được khi chạy trực tiếp `python mcp_server_powerbi.py`
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from powerbi_agent.app import ADOMD_LOADED, main, mcp  # noqa: F401
from powerbi_agent.discovery import find_active_pbi_ports  # noqa: F401 — cli.py dùng
from powerbi_agent.util import MAX_ROWS, log  # noqa: F401

# Back-compat alias (tên private cũ, phòng script ngoài từng import)
_short_err = __import__("powerbi_agent.util", fromlist=["short_err"]).short_err
_df_to_markdown_capped = __import__("powerbi_agent.util", fromlist=["df_to_markdown_capped"]).df_to_markdown_capped

if __name__ == "__main__":
    main()
