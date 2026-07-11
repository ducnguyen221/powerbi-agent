import os
import sys
import glob
import re
import logging
import requests

# Ghi log ra stderr (KHÔNG dùng stdout — sẽ làm hỏng luồng JSON-RPC của MCP stdio)
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s [powerbi-mcp] %(levelname)s: %(message)s",
)
log = logging.getLogger("powerbi-mcp")

# Số dòng tối đa trả về cho mỗi truy vấn để tránh tràn context / OOM.
# Có thể ghi đè qua biến môi trường POWERBI_MAX_ROWS.
try:
    MAX_ROWS = int(os.getenv("POWERBI_MAX_ROWS", "1000"))
except ValueError:
    MAX_ROWS = 1000


# ==========================================
# 0. NẠP ADOMD.NET ĐA-PHIÊN-BẢN (PORTABLE)
# ==========================================
# Bản gốc hardcode đúng 1 đường dẫn SSMS 21. Bản này dò nhiều vị trí phổ biến
# để chạy được trên máy bất kỳ (SSMS bản khác, ADOMD.NET standalone, hoặc GAC).
# Ưu tiên override thủ công qua biến môi trường ADOMD_LIB_DIR.

ADOMD_DLL = "Microsoft.AnalysisServices.AdomdClient.dll"


def _candidate_adomd_dirs():
    """Sinh danh sách thư mục ứng viên có thể chứa AdomdClient.dll, theo thứ tự ưu tiên."""
    dirs = []

    # 1. Override tường minh từ môi trường (đường dẫn tới thư mục chứa DLL)
    env_dir = os.getenv("ADOMD_LIB_DIR")
    if env_dir:
        dirs.append(env_dir)

    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    # 2. SQL Server Management Studio (mọi phiên bản: 18, 19, 20, 21, ...)
    for base in (pf, pf86):
        dirs += glob.glob(os.path.join(base, "Microsoft SQL Server Management Studio*", "*", "Common7", "IDE"))
        dirs += glob.glob(os.path.join(base, "Microsoft SQL Server Management Studio*", "Common7", "IDE"))

    # 3. ADOMD.NET cài standalone (MSI "Analysis Services client libraries")
    for base in (pf, pf86):
        dirs += glob.glob(os.path.join(base, "Microsoft.NET", "ADOMD.NET", "*"))

    # 4. SQL Server SDK assemblies
    for base in (pf, pf86):
        dirs += glob.glob(os.path.join(base, "Microsoft SQL Server", "*", "SDK", "Assemblies"))

    # 5. Power BI Desktop / Excel cài kèm bộ thư viện AS (ít gặp nhưng có)
    dirs += glob.glob(os.path.join(pf, "Microsoft Power BI Desktop", "bin"))

    # Khử trùng lặp giữ nguyên thứ tự
    seen = set()
    uniq = []
    for d in dirs:
        if d and d not in seen and os.path.isdir(d):
            seen.add(d)
            uniq.append(d)
    return uniq


def _load_adomd():
    """Thử nạp AdomdClient: dò thư mục có DLL trước, cuối cùng thử GAC. Trả về True nếu thành công."""
    try:
        import clr
    except Exception as e:  # pythonnet chưa sẵn sàng
        log.warning("Không import được pythonnet/clr (%s).", e)
        return False

    # Dò các thư mục ứng viên có chứa DLL và thêm vào sys.path
    for d in _candidate_adomd_dirs():
        if os.path.exists(os.path.join(d, ADOMD_DLL)):
            if d not in sys.path:
                sys.path.append(d)
            try:
                clr.AddReference("Microsoft.AnalysisServices.AdomdClient")
                log.info("Đã nạp ADOMD.NET từ: %s", d)
                return True
            except Exception:
                continue  # thử thư mục kế tiếp

    # Phương án cuối: DLL đã đăng ký trong GAC -> AddReference theo tên là đủ
    try:
        clr.AddReference("Microsoft.AnalysisServices.AdomdClient")
        log.info("Đã nạp ADOMD.NET từ GAC.")
        return True
    except Exception as e:
        log.warning(
            "Chưa nạp được ADOMD.NET (%s). Các tool local sẽ báo lỗi cho tới khi cài "
            "ADOMD.NET / SSMS. Phần Power BI Service (cloud) vẫn hoạt động bình thường. "
            "Có thể trỏ thủ công qua biến môi trường ADOMD_LIB_DIR.",
            e,
        )
        return False


ADOMD_LOADED = _load_adomd()

from mcp.server.fastmcp import FastMCP
from pyadomd import Pyadomd
import pandas as pd
from msal import ConfidentialClientApplication
from dotenv import load_dotenv

# Tải cấu hình bảo mật từ file .env (nằm cùng thư mục với script này)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Khởi tạo MCP Server với tên gọi định danh
mcp = FastMCP("PowerBI-Bridge-Server")


def _short_err(err, limit: int = 400) -> str:
    """Rút gọn thông điệp lỗi trước khi trả về cho agent (tránh đổ chuỗi dài/nhạy cảm)."""
    msg = str(err)
    return msg if len(msg) <= limit else msg[:limit] + " …[đã cắt]"


def _df_to_markdown_capped(df, max_rows: int) -> str:
    """Chuyển DataFrame -> bảng Markdown, cắt bớt nếu vượt quá max_rows."""
    total = len(df)
    if max_rows and total > max_rows:
        note = (
            f"\n\n> ⚠️ Kết quả có {total} dòng, chỉ hiển thị {max_rows} dòng đầu. "
            "Hãy dùng TOPN / bộ lọc để thu hẹp truy vấn."
        )
        return df.head(max_rows).to_markdown(index=False) + note
    return df.to_markdown(index=False)


# ==========================================
# 1. PHÂN HỆ POWER BI DESKTOP (LOCAL)
# ==========================================

def find_active_pbi_ports():
    """
    Quét tìm cổng kết nối của các phiên bản Power BI Desktop đang chạy.
    Ưu tiên tìm thông qua cổng TCP đang lắng nghe của tiến trình msmdsrv.exe.
    Nếu thất bại, sẽ fallback về quét file msmdsrv.port.txt trên đĩa.
    """
    active_instances = []
    ports_found = set()

    # Cách 1: Truy vấn cổng TCP qua PowerShell (Dành cho Windows)
    if sys.platform == 'win32':
        try:
            import subprocess
            # Lệnh PowerShell lấy các cổng TCP đang lắng nghe của tiến trình msmdsrv
            cmd = 'powershell -NoProfile -Command "Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -in (Get-Process -Name msmdsrv -ErrorAction SilentlyContinue).Id } | Select-Object -ExpandProperty LocalPort"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    port_str = line.strip()
                    if port_str.isdigit():
                        port = int(port_str)
                        if port not in ports_found:
                            ports_found.add(port)
                            active_instances.append({
                                "port": port_str,
                                "workspace_id": f"tcp_{port_str}"
                            })
        except Exception:
            pass  # Nếu lỗi, tiếp tục thử các cách sau

    if active_instances:
        return active_instances

    # Cách 2: Quét file msmdsrv.port.txt truyền thống ở AppData\\Local (MSI)
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        workspace_dir = os.path.join(local_app_data, 'Microsoft', 'Power BI Desktop', 'AnalysisServicesWorkspaces')
        if os.path.exists(workspace_dir):
            port_files = glob.glob(os.path.join(workspace_dir, '*', 'Data', 'msmdsrv.port.txt'))
            for port_file in port_files:
                try:
                    with open(port_file, 'r', encoding='utf-16') as f:
                        port = f.read().strip()
                    parent_dir = os.path.dirname(os.path.dirname(port_file))
                    dir_name = os.path.basename(parent_dir)
                    if port.isdigit() and int(port) not in ports_found:
                        ports_found.add(int(port))
                        active_instances.append({
                            "port": port,
                            "workspace_id": dir_name
                        })
                except Exception:
                    continue

    # Cách 3: Thử quét trong thư mục LocalCache của Store App nếu cách 2 không có
    if local_app_data and not active_instances:
        store_workspaces = glob.glob(os.path.join(
            local_app_data, 'Packages', 'Microsoft.MicrosoftPowerBIDesktop*',
            'LocalCache', 'Local', 'Microsoft', 'Power BI Desktop', 'AnalysisServicesWorkspaces'
        ))
        for workspace_dir in store_workspaces:
            if os.path.exists(workspace_dir):
                port_files = glob.glob(os.path.join(workspace_dir, '*', 'Data', 'msmdsrv.port.txt'))
                for port_file in port_files:
                    try:
                        with open(port_file, 'r', encoding='utf-16') as f:
                            port = f.read().strip()
                        parent_dir = os.path.dirname(os.path.dirname(port_file))
                        dir_name = os.path.basename(parent_dir)
                        if port.isdigit() and int(port) not in ports_found:
                            ports_found.add(int(port))
                            active_instances.append({
                                "port": port,
                                "workspace_id": dir_name
                            })
                    except Exception:
                        continue

    return active_instances


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
            output += f"- Cổng: {inst['port']} | Lỗi lấy tên Model (có thể do thiếu driver ADOMD.NET hoặc cổng bận): {_short_err(e)}\n"

    return output

@mcp.tool()
def execute_dax_local(port: str, model_id: str, dax_query: str, max_rows: int = MAX_ROWS) -> str:
    """
    Thực thi một truy vấn DAX trực tiếp lên báo cáo Power BI Desktop đang mở.
    - port: Cổng kết nối (ví dụ: '51234')
    - model_id: Tên catalog/model ID lấy từ công cụ list_local_reports
    - dax_query: Câu lệnh DAX (ví dụ: 'EVALUATE TableName')
    - max_rows: Số dòng tối đa trả về (mặc định 1000). Đặt 0 để bỏ giới hạn.
    """
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
                return _df_to_markdown_capped(df, max_rows)
    except Exception as e:
        log.exception("execute_dax_local thất bại")
        return f"Lỗi khi thực thi DAX cục bộ: {_short_err(e)}"

# ==========================================
# 2. PHÂN HỆ POWER BI SERVICE (CLOUD)
# ==========================================

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

@mcp.tool()
def execute_dax_service(dataset_id: str, dax_query: str, max_rows: int = MAX_ROWS) -> str:
    """
    Truy vấn dữ liệu từ Dataset đã xuất bản trên Cloud Power BI Service thông qua REST API.
    - dataset_id: Mã GUID của dataset cần truy vấn.
    - dax_query: Câu lệnh DAX (ví dụ: 'EVALUATE SUMMARIZECOLUMNS(...)')
    - max_rows: Số dòng tối đa trả về (mặc định 1000). Đặt 0 để bỏ giới hạn.
    """
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
            return f"Lỗi gọi API Power BI (Code {response.status_code}): {_short_err(response.text)}"

        res_data = response.json()
        tables = res_data.get('results', [{}])[0].get('tables', [])
        if not tables:
            return "Không có dữ liệu trả về từ Dataset."

        # Chuyển kết quả JSON sang bảng định dạng Markdown
        rows = tables[0].get('rows', [])
        df = pd.DataFrame(rows)
        return _df_to_markdown_capped(df, max_rows)

    except Exception as e:
        log.exception("execute_dax_service thất bại")
        return f"Lỗi kết nối Power BI Service: {_short_err(e)}"

# Chạy server thông qua luồng giao tiếp tiêu chuẩn stdio
if __name__ == "__main__":
    mcp.run(transport="stdio")
