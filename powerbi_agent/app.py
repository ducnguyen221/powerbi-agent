"""Khởi tạo MCP server: nạp ADOMD → tạo FastMCP → đăng ký tool.

THỨ TỰ QUAN TRỌNG: load_adomd() phải chạy TRƯỚC import pyadomd (tools_query),
vì pyadomd resolve assembly AdomdClient ngay lúc import.
"""

import os

from powerbi_agent.adomd import load_adomd, load_tabular
from powerbi_agent.util import log  # noqa: F401 — khởi tạo logging stderr sớm

ADOMD_LOADED = load_adomd()
TABULAR_LOADED = load_tabular()

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Tải cấu hình bảo mật từ file .env (nằm ở thư mục gốc repo — cha của package này)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_REPO_ROOT, ".env"))

# Khởi tạo MCP Server với tên gọi định danh (giữ nguyên tên từ v0 — host đã đăng ký)
mcp = FastMCP("PowerBI-Bridge-Server")

from powerbi_agent import tools_distill, tools_query, tools_tom  # sau load_adomd()

tools_query.register(mcp)
tools_tom.register(mcp, TABULAR_LOADED)
tools_distill.register(mcp)


def main():
    """Chạy server qua stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
