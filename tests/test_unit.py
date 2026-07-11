"""Unit tests — không cần Power BI Desktop hay ADOMD.NET."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from powerbi_agent import policy
from powerbi_agent.adomd import candidate_adomd_dirs
from powerbi_agent.util import df_to_markdown_capped, short_err


class TestUtil:
    def test_short_err_passthrough(self):
        assert short_err("ngắn") == "ngắn"

    def test_short_err_caps_long_messages(self):
        msg = "x" * 1000
        out = short_err(msg)
        assert len(out) < 450
        assert out.endswith("…[đã cắt]")

    def test_df_markdown_no_cap(self):
        df = pd.DataFrame({"a": [1, 2]})
        out = df_to_markdown_capped(df, 100)
        assert "⚠️" not in out

    def test_df_markdown_caps_rows(self):
        df = pd.DataFrame({"a": range(50)})
        out = df_to_markdown_capped(df, 10)
        assert "50 dòng" in out and "10 dòng đầu" in out

    def test_df_markdown_zero_disables_cap(self):
        df = pd.DataFrame({"a": range(50)})
        assert "⚠️" not in df_to_markdown_capped(df, 0)


class TestAdomdProbe:
    def test_candidate_dirs_returns_list(self):
        assert isinstance(candidate_adomd_dirs(), list)

    def test_env_override_first(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ADOMD_LIB_DIR", str(tmp_path))
        dirs = candidate_adomd_dirs()
        assert dirs and dirs[0] == str(tmp_path)


class TestPolicy:
    @pytest.fixture(autouse=True)
    def enable(self, monkeypatch):
        monkeypatch.setenv("POWERBI_AGGREGATE_ONLY", "1")

    @pytest.mark.parametrize("dax", [
        "EVALUATE 'Sales'",
        "EVALUATE Sales",
        "evaluate 'Bảng Khách Hàng'",
        "EVALUATE ALL('Sales')",
        "EVALUATE ALLNOBLANKROW('Sales')",
    ])
    def test_blocks_raw_dumps(self, dax):
        allowed, reason = policy.check_dax(dax)
        assert not allowed and "SUMMARIZECOLUMNS" in reason

    @pytest.mark.parametrize("dax", [
        'EVALUATE SUMMARIZECOLUMNS(Cal[Year], "Qty", [Total Qty])',
        "EVALUATE TOPN(10, SUMMARIZECOLUMNS(Cal[Year]))",
        'EVALUATE ROW("KQ", [Total])',
        "EVALUATE FILTER(SUMMARIZECOLUMNS(Cal[Year]), TRUE())",
    ])
    def test_allows_aggregates(self, dax):
        allowed, _ = policy.check_dax(dax)
        assert allowed

    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.setenv("POWERBI_AGGREGATE_ONLY", "0")
        allowed, _ = policy.check_dax("EVALUATE 'Sales'")
        assert allowed  # M0: pass-through; M1 đảo mặc định


class TestBackCompat:
    """Shim mcp_server_powerbi phải giữ nguyên bề mặt import cho host/cli."""

    def test_shim_exports(self):
        import mcp_server_powerbi as m
        assert callable(m.find_active_pbi_ports)
        assert hasattr(m, "mcp") and hasattr(m, "ADOMD_LOADED")

    def test_three_tools_registered(self):
        import asyncio

        import mcp_server_powerbi as m
        tools = asyncio.run(m.mcp.list_tools())
        names = {t.name for t in tools}
        assert {"list_local_reports", "execute_dax_local", "execute_dax_service"} <= names
