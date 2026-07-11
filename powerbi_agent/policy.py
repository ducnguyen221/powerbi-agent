"""Tầng chính sách an toàn dữ liệu (M1 — xem ROADMAP.md §M1).

M0: khung + hook, mặc định pass-through để không đổi hành vi bản đang chạy.
M1 sẽ bật `aggregate_only` mặc định + PII blocklist + audit log.
Bật sớm ngay bây giờ bằng biến môi trường POWERBI_AGGREGATE_ONLY=1.
"""

import os
import re

# Các pattern DAX "dump bảng thô" — EVALUATE thẳng vào bảng/ALL() không qua tổng hợp.
_RAW_DUMP_PATTERNS = [
    # EVALUATE 'Tên bảng'  /  EVALUATE Bảng  (không có hàm bọc ngoài)
    re.compile(r"^\s*EVALUATE\s+'[^']+'\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*EVALUATE\s+[A-Za-z_][\w ]*\s*$", re.IGNORECASE | re.MULTILINE),
    # EVALUATE ALL('Bảng') / ALLNOBLANKROW(...)
    re.compile(r"^\s*EVALUATE\s+ALL(NOBLANKROW)?\s*\(", re.IGNORECASE | re.MULTILINE),
]

_REWRITE_HINT = (
    "Truy vấn bị chặn bởi chính sách an toàn dữ liệu (aggregate-only): "
    "không dump dữ liệu thô từng dòng vào context. Hãy viết lại bằng "
    "SUMMARIZECOLUMNS / GROUPBY / TOPN(n nhỏ) hoặc truy vấn measure "
    "(EVALUATE ROW(\"KQ\", [Measure])). Dữ liệu thô nên ở lại trong engine."
)


def aggregate_only_enabled() -> bool:
    """M0: mặc định TẮT (giữ hành vi cũ). M1 sẽ đảo mặc định thành BẬT."""
    return os.getenv("POWERBI_AGGREGATE_ONLY", "0") == "1"


def check_dax(dax_query: str) -> tuple[bool, str]:
    """Kiểm tra 1 câu DAX theo policy. Trả (allowed, reason_nếu_chặn).

    Best-effort guard chống rò rỉ do SƠ Ý — không phải bảo mật cứng
    (bảo mật cứng = RLS trên model + service principal quyền tối thiểu).
    """
    if not aggregate_only_enabled():
        return True, ""
    for pat in _RAW_DUMP_PATTERNS:
        if pat.search(dax_query):
            return False, _REWRITE_HINT
    return True, ""
