import sys
import os
import argparse
import json
import io

# Cấu hình encoding UTF-8 cho stdout để tránh lỗi Unicode trên Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Dùng CHUNG bộ nạp ADOMD.NET đa-phiên-bản của MCP server (không hardcode đường dẫn SSMS).
# Import mcp_server_powerbi sẽ tự dò & nạp ADOMD.NET động (mọi SSMS / standalone / GAC).
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root — script nằm trong scripts/
from mcp_server_powerbi import find_active_pbi_ports
from pyadomd import Pyadomd
import pandas as pd

def cmd_list(args):
    instances = find_active_pbi_ports()
    if not instances:
        print(json.dumps({"status": "success", "data": []}))
        return
        
    results = []
    for inst in instances:
        port = inst['port']
        try:
            conn_str = f"Provider=MSOLAP;Data Source=localhost:{port};"
            with Pyadomd(conn_str) as conn:
                with conn.cursor().execute("SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS") as cur:
                    catalogs = cur.fetchall()
                    catalog_name = catalogs[0][0] if catalogs else "Unknown"
            results.append({
                "port": port,
                "model_id": catalog_name,
                "status": "connected"
            })
        except Exception as e:
            results.append({
                "port": port,
                "model_id": "Unknown",
                "status": "error",
                "error": str(e)
            })
            
    print(json.dumps({"status": "success", "data": results}, indent=2, ensure_ascii=False))

def cmd_query(args):
    port = args.port
    model_id = args.model_id
    query = args.dax
    
    conn_str = f"Provider=MSOLAP;Data Source=localhost:{port};Catalog={model_id};"
    try:
        with Pyadomd(conn_str) as conn:
            with conn.cursor().execute(query) as cur:
                data = cur.fetchall()
                if not data:
                    print(json.dumps({"status": "success", "data": "Truy vấn thành công nhưng không có dữ liệu trả về."}))
                    return
                
                columns = [desc[0] for desc in cur.description] if cur.description else None
                df = pd.DataFrame(data, columns=columns)
                if args.format == 'markdown':
                    print(df.to_markdown(index=False))
                else:
                    records = df.to_dict(orient='records')
                    print(json.dumps({"status": "success", "data": records}, indent=2, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}, indent=2, ensure_ascii=False))

def cmd_tables(args):
    port = args.port
    model_id = args.model_id
    
    conn_str = f"Provider=MSOLAP;Data Source=localhost:{port};Catalog={model_id};"
    try:
        with Pyadomd(conn_str) as conn:
            tables_query = "SELECT [Name] FROM $SYSTEM.TMSCHEMA_TABLES"
            with conn.cursor().execute(tables_query) as cur:
                tables = cur.fetchall()
                if tables:
                    filtered_tables = [t[0] for t in tables if not t[0].startswith('LocalDateTable_') and not t[0].startswith('DateTableTemplate_')]
                    if args.format == 'markdown':
                        df = pd.DataFrame(filtered_tables, columns=["Table Name"])
                        print(df.to_markdown(index=False))
                    else:
                        print(json.dumps({"status": "success", "data": filtered_tables}, indent=2, ensure_ascii=False))
                else:
                    print(json.dumps({"status": "success", "data": []}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}, indent=2, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description="CLI Tool để tương tác trực tiếp với Power BI Desktop Local.")
    subparsers = parser.add_subparsers(dest="command", help="Các lệnh hỗ trợ")
    
    # Subcommand: list
    subparsers.add_parser("list", help="Liệt kê các báo cáo đang mở và cổng kết nối.")
    
    # Subcommand: query
    parser_query = subparsers.add_parser("query", help="Thực thi truy vấn DAX/DMV lên báo cáo đang mở.")
    parser_query.add_argument("port", type=str, help="Cổng kết nối")
    parser_query.add_argument("model_id", type=str, help="Mã model/catalog")
    parser_query.add_argument("dax", type=str, help="Câu lệnh DAX")
    parser_query.add_argument("--format", type=str, choices=['json', 'markdown'], default='markdown', help="Định dạng kết quả trả về")
    
    # Subcommand: tables
    parser_tables = subparsers.add_parser("tables", help="Lấy danh sách các bảng trong mô hình.")
    parser_tables.add_argument("port", type=str, help="Cổng kết nối")
    parser_tables.add_argument("model_id", type=str, help="Mã model/catalog")
    parser_tables.add_argument("--format", type=str, choices=['json', 'markdown'], default='markdown', help="Định dạng kết quả")

    args = parser.parse_args()
    
    if args.command == "list":
        cmd_list(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "tables":
        cmd_tables(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
