"""Nạp ADOMD.NET đa-phiên-bản (portable).

Bản gốc hardcode đúng 1 đường dẫn SSMS 21. Bản này dò nhiều vị trí phổ biến
để chạy được trên máy bất kỳ (SSMS bản khác, ADOMD.NET standalone, hoặc GAC).
Ưu tiên override thủ công qua biến môi trường ADOMD_LIB_DIR.

QUAN TRỌNG: load_adomd() phải được gọi TRƯỚC khi import pyadomd ở bất kỳ đâu.
"""

import glob
import os
import sys

from powerbi_agent.util import log

ADOMD_DLL = "Microsoft.AnalysisServices.AdomdClient.dll"


def candidate_adomd_dirs():
    """Sinh danh sách thư mục ứng viên có thể chứa AdomdClient.dll, theo thứ tự ưu tiên."""
    dirs = []

    # 1. Override tường minh từ môi trường (đường dẫn tới thư mục chứa DLL)
    env_dir = os.getenv("ADOMD_LIB_DIR")
    if env_dir:
        dirs.append(env_dir)

    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    # 2. SQL Server Management Studio (mọi phiên bản: 18, 19, 20, 21, 22, ...)
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


def load_adomd():
    """Thử nạp AdomdClient: dò thư mục có DLL trước, cuối cùng thử GAC. Trả về True nếu thành công."""
    try:
        import clr
    except Exception as e:  # pythonnet chưa sẵn sàng
        log.warning("Không import được pythonnet/clr (%s).", e)
        return False

    # Dò các thư mục ứng viên có chứa DLL và thêm vào sys.path
    for d in candidate_adomd_dirs():
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
