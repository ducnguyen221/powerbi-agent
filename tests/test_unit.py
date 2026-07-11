"""Unit tests — không cần Power BI Desktop hay ADOMD.NET."""

import json
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

    def test_opt_out_with_env_zero(self, monkeypatch):
        monkeypatch.setenv("POWERBI_AGGREGATE_ONLY", "0")
        allowed, _ = policy.check_dax("EVALUATE 'Sales'")
        assert allowed


class TestPolicyM1:
    def test_default_is_on(self, monkeypatch):
        monkeypatch.delenv("POWERBI_AGGREGATE_ONLY", raising=False)
        allowed, reason = policy.check_dax("EVALUATE 'Sales'")
        assert not allowed and "aggregate-only" in reason

    def test_pii_blocklist_blocks(self, tmp_path, monkeypatch):
        pf = tmp_path / "policy.json"
        pf.write_text(
            '{"blocked_columns": ["\'Khách hàng\'[Số điện thoại]"]}', encoding="utf-8"
        )
        monkeypatch.setenv("POWERBI_POLICY_FILE", str(pf))
        monkeypatch.setenv("POWERBI_AUDIT_DIR", str(tmp_path / "audit"))
        dax = "EVALUATE SUMMARIZECOLUMNS('Khách hàng'[Số điện thoại], \"n\", [Đếm KH])"
        allowed, reason = policy.check_dax(dax)
        assert not allowed and "PII blocklist" in reason
        # audit đã ghi verdict blocked_pii
        files = list((tmp_path / "audit").glob("*.jsonl"))
        assert files and "blocked_pii" in files[0].read_text(encoding="utf-8")

    def test_pii_allows_other_columns(self, tmp_path, monkeypatch):
        pf = tmp_path / "policy.json"
        pf.write_text('{"blocked_columns": ["[Số điện thoại]"]}', encoding="utf-8")
        monkeypatch.setenv("POWERBI_POLICY_FILE", str(pf))
        allowed, _ = policy.check_dax("EVALUATE SUMMARIZECOLUMNS('KH'[Phân khúc])")
        assert allowed

    def test_audit_never_breaks_query(self, monkeypatch):
        monkeypatch.setenv("POWERBI_AUDIT_DIR", "Z:/duong/dan/khong/ton/tai")
        policy.audit("t", "EVALUATE ROW(1)", "allowed", 1)  # không raise là PASS

    def test_dimension_cap(self, monkeypatch):
        monkeypatch.delenv("POWERBI_AGGREGATE_ONLY", raising=False)
        df_dim = pd.DataFrame({"khu_vuc": ["A", "B"], "v": [1, 2]})
        df_num = pd.DataFrame({"v": [1.0, 2.0]})
        assert policy.cap_dimension_rows(df_dim, 1000) == policy.DIMENSION_ROW_CAP
        assert policy.cap_dimension_rows(df_dim, 0) == policy.DIMENSION_ROW_CAP
        assert policy.cap_dimension_rows(df_num, 1000) == 1000
        monkeypatch.setenv("POWERBI_AGGREGATE_ONLY", "0")
        assert policy.cap_dimension_rows(df_dim, 1000) == 1000


class TestPbir:
    def test_new_guid_format(self):
        from powerbi_agent import pbir
        g = pbir.new_guid()
        assert len(g) == 20 and all(c in "0123456789abcdef" for c in g)

    def test_projection_measure(self):
        from powerbi_agent import pbir
        p = pbir.projection("Measure", "Công thức", "Tổng TB")
        assert p["field"]["Measure"]["Expression"]["SourceRef"]["Entity"] == "Công thức"
        assert p["queryRef"] == "Công thức.Tổng TB" and p["nativeQueryRef"] == "Tổng TB"

    def test_projection_rejects_bad_kind(self):
        from powerbi_agent import pbir
        with pytest.raises(ValueError):
            pbir.projection("Hierarchy", "T", "C")

    def test_rebind_replaces_role(self):
        from powerbi_agent import pbir
        v = {"visual": {"query": {"queryState": {"Data": {"projections": [{"queryRef": "Old.X"}]}}}}}
        pbir.rebind_query_state(v, {"Data": [{"type": "Measure", "entity": "M", "property": "Doanh thu"}]})
        projs = v["visual"]["query"]["queryState"]["Data"]["projections"]
        assert len(projs) == 1 and projs[0]["queryRef"] == "M.Doanh thu"

    def test_deep_sanitize_covers_style_refs(self):
        from powerbi_agent import pbir
        v = {
            "visual": {
                "visualType": "cardVisual",
                "query": {"queryState": {"Data": {"projections": [
                    {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Công thức"}},
                               "Property": "TB PTM"}},
                     "queryRef": "Công thức.TB PTM", "nativeQueryRef": "TB PTM"}]}}},
                "visualContainerObjects": {"x": [{"sel": "Công thức.TB PTM"}]},
            },
            "filterConfig": {"filters": [{"field": "bí mật"}]},
        }
        e, p = pbir.collect_field_names(v)
        m = pbir.build_sanitize_map(e, p)
        pbir.deep_sanitize(v, m)
        s = json.dumps(v, ensure_ascii=False)
        assert "Công thức" not in s and "TB PTM" not in s
        assert "filterConfig" not in v
        assert "TEMPLATE_TABLE" in s

    def test_deep_sanitize_image_resource_names(self):
        from powerbi_agent import pbir
        v = {"visual": {"visualType": "image", "objects": {"general": [
            {"properties": {"imageUrl": {"expr": {"ResourcePackageItem": {
                "ItemName": "client-logo47855673.png"}}}}}]}}}
        pbir.deep_sanitize(v, {})
        assert "client-logo" not in json.dumps(v)
        assert "TEMPLATE_IMAGE.png" in json.dumps(v)


class TestBackCompat:
    """Shim mcp_server_powerbi phải giữ nguyên bề mặt import cho host/cli."""

    def test_shim_exports(self):
        import mcp_server_powerbi as m
        assert callable(m.find_active_pbi_ports)
        assert hasattr(m, "mcp") and hasattr(m, "ADOMD_LOADED")

    def test_six_tools_registered(self):
        import asyncio

        import mcp_server_powerbi as m
        tools = asyncio.run(m.mcp.list_tools())
        names = {t.name for t in tools}
        assert {
            "list_local_reports", "execute_dax_local", "execute_dax_service",
            "add_measure_local", "add_relationship_local", "distill_model_schema",
        } <= names


class TestDistill:
    def test_output_dir_param_wins(self, monkeypatch):
        from powerbi_agent.tools_distill import _resolve_output_dir
        monkeypatch.setenv("POWERBI_DISTILL_DIR", "C:/env-dir")
        assert _resolve_output_dir("C:/param-dir") == "C:/param-dir"

    def test_output_dir_env_fallback(self, monkeypatch):
        from powerbi_agent.tools_distill import _resolve_output_dir
        monkeypatch.setenv("POWERBI_DISTILL_DIR", "C:/env-dir")
        assert _resolve_output_dir(None) == "C:/env-dir"

    def test_output_dir_default_outside_repo(self, monkeypatch):
        from powerbi_agent.tools_distill import _resolve_output_dir
        monkeypatch.delenv("POWERBI_DISTILL_DIR", raising=False)
        out = _resolve_output_dir(None)
        assert ".powerbi-agent" in out  # NGOÀI repo — không commit schema khách
