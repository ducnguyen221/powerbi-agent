"""Helpers đọc/ghi PBIR (Power BI Enhanced Report Format — .pbip *.Report/definition).

Luật cứng (đúc từ thực chiến — xem skill powerbi-report-design):
- CHỈ sửa khi file .pbip ĐÓNG trong Power BI Desktop (Ctrl+S phiên mở sẽ đè mất JSON).
- Ghi UTF-8 KHÔNG BOM.
- Clone-and-rebind: giữ nguyên `visualContainerObjects` (style), chỉ đổi name/position/
  queryState/visualType.
"""

import json
import os
import secrets


def new_guid() -> str:
    """GUID kiểu PBIR: 20 ký tự hex thường (khớp format các visual/page có sẵn)."""
    return secrets.token_hex(10)


def read_json(path: str):
    with open(path, encoding="utf-8-sig") as f:  # utf-8-sig nuốt BOM nếu lỡ có
        return json.load(f)


def write_json_no_bom(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def resolve_definition_dir(report_path: str) -> str:
    """Nhận đường dẫn linh hoạt (file .pbip, folder *.Report, hoặc folder definition)
    → trả về folder definition. Raise ValueError nếu không tìm thấy cấu trúc PBIR."""
    p = report_path.rstrip("\\/")
    if p.lower().endswith(".pbip"):
        base = os.path.splitext(p)[0]
        p = base + ".Report"
    if os.path.basename(p).lower() == "definition":
        candidate = p
    else:
        candidate = os.path.join(p, "definition")
    if not os.path.isdir(os.path.join(candidate, "pages")):
        raise ValueError(
            f"Không thấy cấu trúc PBIR tại '{report_path}' (cần *.Report/definition/pages). "
            "File .pbix phải Save As .pbip (bật Preview 'Power BI Project (.pbip) save option' + PBIR) trước."
        )
    return candidate


def find_page(definition_dir: str, page: str) -> tuple[str, dict]:
    """Tìm trang theo GUID hoặc displayName. Trả (page_dir, page_json)."""
    pages_root = os.path.join(definition_dir, "pages")
    # thử GUID trực tiếp
    direct = os.path.join(pages_root, page, "page.json")
    if os.path.exists(direct):
        return os.path.join(pages_root, page), read_json(direct)
    # dò theo displayName
    for d in os.listdir(pages_root):
        pj = os.path.join(pages_root, d, "page.json")
        if os.path.exists(pj):
            data = read_json(pj)
            if data.get("displayName") == page:
                return os.path.join(pages_root, d), data
    raise ValueError(f"Không tìm thấy trang '{page}'. Trang phải là GUID folder hoặc displayName chính xác.")


def list_visuals(page_dir: str) -> list[tuple[str, dict]]:
    """Trả [(visual_id, visual_json)] của 1 trang."""
    vroot = os.path.join(page_dir, "visuals")
    out = []
    if not os.path.isdir(vroot):
        return out
    for d in sorted(os.listdir(vroot)):
        vj = os.path.join(vroot, d, "visual.json")
        if os.path.exists(vj):
            out.append((d, read_json(vj)))
    return out


def projection(kind: str, entity: str, prop: str, display_name: str | None = None,
               active: bool | None = None) -> dict:
    """Sinh 1 projection entry chuẩn PBIR. kind = 'Measure' | 'Column'."""
    if kind not in ("Measure", "Column"):
        raise ValueError(f"kind phải là 'Measure' hoặc 'Column', nhận '{kind}'")
    entry = {
        "field": {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }
    if display_name:
        entry["displayName"] = display_name
    if active is not None:
        entry["active"] = active
    return entry


def rebind_query_state(visual_obj: dict, fields: dict) -> None:
    """Thay projections của các Role có trong `fields` (Role khác giữ nguyên).
    fields = {Role: [{"type": "Measure"|"Column", "entity": ..., "property": ...,
                      "displayName"?: ..., "active"?: bool}]}"""
    query = visual_obj.setdefault("visual", {}).setdefault("query", {})
    qs = query.setdefault("queryState", {})
    for role, items in fields.items():
        projections = []
        for it in items:
            projections.append(projection(
                it["type"], it["entity"], it["property"],
                it.get("displayName"), it.get("active"),
            ))
        qs[role] = {"projections": projections}
    # sortDefinition của block trỏ field CŨ → bỏ để Desktop dùng sort mặc định
    # (muốn sort tùy chỉnh: đặt lại trong Desktop sau khi nghiệm thu trang)
    query.pop("sortDefinition", None)


def set_title(visual_obj: dict, title: str) -> None:
    """Đặt/ghi đè title text, GIỮ style title có sẵn của block (font/màu/size không đụng)."""
    vco = visual_obj.setdefault("visual", {}).setdefault("visualContainerObjects", {})
    titles = vco.setdefault("title", [{}])
    props = titles[0].setdefault("properties", {})
    escaped = title.replace("'", "''")
    props["text"] = {"expr": {"Literal": {"Value": f"'{escaped}'"}}}


def collect_field_names(obj) -> tuple[set, set]:
    """Gom mọi giá trị của khóa 'Entity' và 'Property' trong cả cây JSON."""
    entities, properties = set(), set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "Entity" and isinstance(v, str):
                    entities.add(v)
                elif k == "Property" and isinstance(v, str):
                    properties.add(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for it in node:
                walk(it)

    walk(obj)
    return entities, properties


def build_sanitize_map(entities: set, properties: set) -> dict[str, str]:
    """Map tên thật → placeholder ổn định (sort để deterministic)."""
    mapping = {}
    for e in sorted(entities):
        mapping[e] = "TEMPLATE_TABLE"
    for i, p in enumerate(sorted(properties), start=1):
        mapping[p] = f"TEMPLATE_FIELD_{i}"
    return mapping


def deep_sanitize(visual_obj: dict, mapping: dict[str, str]) -> None:
    """Thay tên bảng/cột thật bằng placeholder Ở MỌI NƠI trong visual JSON — không chỉ
    queryState mà cả objects/visualContainerObjects (conditional color, dataPoint selector,
    sortDefinition, queryRef string...). Style giữ nguyên; apply_template sẽ rebind lại.

    Thay chuỗi theo tên DÀI TRƯỚC để tránh tên ngắn ăn mất một phần tên dài."""
    keys_desc = sorted(mapping.keys(), key=len, reverse=True)

    def repl_str(s: str) -> str:
        for k in keys_desc:
            if k in s:
                s = s.replace(k, mapping[k])
        return s

    def walk(node):
        if isinstance(node, dict):
            for k in list(node.keys()):
                v = node[k]
                if isinstance(v, str):
                    node[k] = repl_str(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for i, it in enumerate(node):
                if isinstance(it, str):
                    node[i] = repl_str(it)
                else:
                    walk(it)

    # filter mức visual chứa field + giá trị lọc thật → bỏ hẳn
    visual_obj.pop("filterConfig", None)
    walk(visual_obj)

    # textbox: nội dung chữ là văn bản nghiệp vụ → thay bằng placeholder
    v = visual_obj.get("visual", {})
    if v.get("visualType") == "textbox":
        gen = v.get("objects", {}).get("general", [])
        for item in gen:
            paras = item.get("properties", {}).get("paragraphs", [])
            for p in paras:
                for run in p.get("textRuns", []):
                    if "value" in run:
                        run["value"] = "TEMPLATE_TEXT"


def roles_of(visual_obj: dict) -> list[str]:
    return sorted(visual_obj.get("visual", {}).get("query", {}).get("queryState", {}).keys())


def fields_of(visual_obj: dict) -> dict:
    """Rút gọn binding hiện tại: {Role: [queryRef,...]} — phục vụ blueprint."""
    out = {}
    qs = visual_obj.get("visual", {}).get("query", {}).get("queryState", {})
    for role, role_obj in qs.items():
        out[role] = [p.get("queryRef", "?") for p in role_obj.get("projections", [])]
    return out
