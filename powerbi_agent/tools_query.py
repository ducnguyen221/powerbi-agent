"""Tool truy vấn: Desktop (ADOMD) + Service (REST). Đăng ký vào FastMCP qua register()."""

import os

import pandas as pd
import requests
from msal import ConfidentialClientApplication
from pyadomd import Pyadomd  # LƯU Ý: adomd.load_adomd() phải chạy trước khi import module này

from powerbi_agent import policy
from powerbi_agent.discovery import find_active_pbi_ports
from powerbi_agent.util import MAX_ROWS, df_to_markdown_capped, log, short_err


def get_azure_token():
    """Lấy Access Token từ Entra ID sử dụng Client ID/Secret từ file cấu hình."""
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    tenant_id = os.getenv("TENANT_ID")

    if not all([client_id, client_secret, tenant_id]):
        raise ValueError("Thiếu cấu hình CLIENT_ID, CLIENT_SECRET hoặc TENANT_ID trong file .env.")

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scope = ["https://analysis.windows.net/powerbi/api/.default"]

    app = ConfidentialClientApplication(client_id, client_secret=client_secret, authority=authority)
    result = app.acquire_token_for_client(scopes=scope)

    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Không thể lấy token: {result.get('error_description')}")


def register(mcp):
    """Đăng ký các tool truy vấn vào instance FastMCP."""

    @mcp.tool()
    def list_local_reports() -> str:
        """Liệt kê các báo cáo Power BI Desktop đang mở trên máy tính kèm thông tin cổng kết nối."""
        instances = find_active_pbi_ports()
        if not instances:
            return "Không tìm thấy phiên bản Power BI Desktop nào đang hoạt động trên máy."

        output = "Các báo cáo đang mở:\n"
        for inst in instances:
            # Lấy tên Model thực tế thông qua việc truy vấn danh mục
            try:
                conn_str = f"Provider=MSOLAP;Data Source=localhost:{inst['port']};"
                with Pyadomd(conn_str) as conn:
                    with conn.cursor().execute("SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS") as cur:
                        catalogs = cur.fetchall()
                        catalog_name = catalogs[0][0] if catalogs else "Unknown"
                output += f"- Cổng: {inst['port']} | Mã Model: {catalog_name}\n"
            except Exception as e:
                output += f"- Cổng: {inst['port']} | Lỗi lấy tên Model (có thể do thiếu driver ADOMD.NET hoặc cổng bận): {short_err(e)}\n"

        return output

    @mcp.tool()
    def execute_dax_local(port: str, model_id: str, dax_query: str, max_rows: int = MAX_ROWS) -> str:
        """
        Thực thi một truy vấn DAX trực tiếp lên báo cáo Power BI Desktop đang mở.
        - port: Cổng kết nối (ví dụ: '51234')
        - model_id: Tên catalog/model ID lấy từ công cụ list_local_reports
        - dax_query: Câu lệnh DAX (ví dụ: 'EVALUATE SUMMARIZECOLUMNS(...)')
        - max_rows: Số dòng tối đa trả về (mặc định 1000). Đặt 0 để bỏ giới hạn.
        """
        allowed, reason = policy.check_dax(dax_query)
        if not allowed:
            return reason
        conn_str = f"Provider=MSOLAP;Data Source=localhost:{port};Catalog={model_id};"
        try:
            with Pyadomd(conn_str) as conn:
                with conn.cursor().execute(dax_query) as cur:
                    data = cur.fetchall()
                    if not data:
                        return "Truy vấn thành công nhưng không có dữ liệu trả về."
                    # Lấy tên cột thực tế từ cursor description
                    columns = [desc[0] for desc in cur.description] if cur.description else None
                    df = pd.DataFrame(data, columns=columns)
                    return df_to_markdown_capped(df, max_rows)
        except Exception as e:
            log.exception("execute_dax_local thất bại")
            return f"Lỗi khi thực thi DAX cục bộ: {short_err(e)}"

    @mcp.tool()
    def execute_dax_service(dataset_id: str, dax_query: str, max_rows: int = MAX_ROWS) -> str:
        """
        Truy vấn dữ liệu từ Dataset đã xuất bản trên Cloud Power BI Service thông qua REST API.
        - dataset_id: Mã GUID của dataset cần truy vấn.
        - dax_query: Câu lệnh DAX (ví dụ: 'EVALUATE SUMMARIZECOLUMNS(...)')
        - max_rows: Số dòng tối đa trả về (mặc định 1000). Đặt 0 để bỏ giới hạn.
        """
        allowed, reason = policy.check_dax(dax_query)
        if not allowed:
            return reason
        try:
            token = get_azure_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # Endpoint chính thức của Power BI để chạy DAX
            url = f"https://api.powerbi.com/v1.0/myorg/datasets/{dataset_id}/executeQueries"

            payload = {
                "queries": [{"query": dax_query}],
                "serializerSettings": {"includeNulls": True}
            }

            response = requests.post(url, json=payload, headers=headers, timeout=(10, 60))
            if response.status_code != 200:
                return f"Lỗi gọi API Power BI (Code {response.status_code}): {short_err(response.text)}"

            res_data = response.json()
            tables = res_data.get('results', [{}])[0].get('tables', [])
            if not tables:
                return "Không có dữ liệu trả về từ Dataset."

            # Chuyển kết quả JSON sang bảng định dạng Markdown
            rows = tables[0].get('rows', [])
            df = pd.DataFrame(rows)
            return df_to_markdown_capped(df, max_rows)

        except Exception as e:
            log.exception("execute_dax_service thất bại")
            return f"Lỗi kết nối Power BI Service: {short_err(e)}"
