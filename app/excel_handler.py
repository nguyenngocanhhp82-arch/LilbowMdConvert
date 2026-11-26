import csv
import datetime
import io
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import openpyxl

from app.logger import log_debug, log_error, log_info, log_warning

def format_cell_value(val: Any, compact_numbers: bool = True, format_dates: bool = True) -> str:
    """
    Định dạng giá trị từng ô:
    - Ngày tháng: YYYY-MM-DD
    - Số thực: 1.0 -> 1, bỏ số 0 vô nghĩa sau dấu phẩy
    - None / NaN / Unnamed: chuỗi rỗng
    """
    if val is None:
        return ""

    # Xử lý ngày tháng
    if isinstance(val, (datetime.datetime, datetime.date)):
        if format_dates:
            if isinstance(val, datetime.datetime) and (val.hour != 0 or val.minute != 0 or val.second != 0):
                return val.strftime("%Y-%m-%d %H:%M:%S")
            return val.strftime("%Y-%m-%d")
        return str(val)

    # Xử lý số thực
    if isinstance(val, float):
        if compact_numbers:
            if val.is_integer():
                return str(int(val))
            # Rút gọn số thực, bỏ số 0 thừa
            s = f"{val:.6f}".rstrip("0").rstrip(".")
            return s
        return str(val)

    # Xử lý số nguyên hoặc boolean
    if isinstance(val, (int, bool)):
        return str(val)

    # Xử lý chuỗi
    s = str(val).strip()
    if s.lower() in {"nan", "none", "null"}:
        return ""
    if re.match(r"^unnamed:\s*\d+$", s, re.IGNORECASE):
        return ""

    # Thay ký tự xuống dòng bên trong ô thành khoảng trắng để không làm vỡ bảng
    s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return s

def export_as_markdown_table(rows: List[List[str]]) -> str:
    """Chuyển danh sách hàng thành bảng Markdown tiêu chuẩn."""
    if not rows:
        return ""

    # Dòng đầu tiên làm tiêu đề
    header = rows[0]
    num_cols = len(header)
    if num_cols == 0:
        return ""

    lines = []
    # Dòng Header
    lines.append("| " + " | ".join(c.replace("|", "\\|") for c in header) + " |")
    # Dòng phân cách
    lines.append("| " + " | ".join("---" for _ in range(num_cols)) + " |")

    # Các dòng dữ liệu
    for row in rows[1:]:
        # Đảm bảo đủ số cột
        padded_row = row + [""] * (num_cols - len(row))
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in padded_row[:num_cols]) + " |")

    return "\n".join(lines) + "\n"

def export_as_csv_block(rows: List[List[str]]) -> str:
    """Chuyển danh sách hàng thành khối code CSV để tiết kiệm tối đa token."""
    if not rows:
        return ""

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for r in rows:
        writer.writerow(r)

    csv_text = output.getvalue().strip()
    return f"```csv\n{csv_text}\n```\n"

def clean_sheet_grid(raw_rows: List[List[str]]) -> List[List[str]]:
    """
    Loại bỏ hàng rỗng và cột rỗng hoàn toàn khỏi dữ liệu sheet.
    """
    if not raw_rows:
        return []

    # 1. Bỏ các hàng rỗng hoàn toàn
    non_empty_rows = [r for r in raw_rows if any(cell.strip() != "" for cell in r)]
    if not non_empty_rows:
        return []

    # Chuẩn hóa độ dài các hàng
    max_cols = max(len(r) for r in non_empty_rows)
    for r in non_empty_rows:
        while len(r) < max_cols:
            r.append("")

    # 2. Tìm các cột rỗng hoàn toàn
    empty_col_indices = set()
    for col_idx in range(max_cols):
        if all(r[col_idx].strip() == "" for r in non_empty_rows):
            empty_col_indices.add(col_idx)

    # 3. Lọc bỏ các cột rỗng
    final_rows: List[List[str]] = []
    for r in non_empty_rows:
        filtered = [r[col_idx] for col_idx in range(max_cols) if col_idx not in empty_col_indices]
        if any(cell.strip() != "" for cell in filtered):
            final_rows.append(filtered)

    return final_rows

def convert_excel_file(path: Path, settings: Dict[str, Any]) -> str:
    """
    Chuyển đổi file Excel (.xlsx, .xlsm, .csv, .xls) sang Markdown.
    - Mỗi sheet thành '## Tên sheet'
    - Kiểu xuất: markdown, csv, hoặc auto (ngưỡng > 50 dòng)
    - data_only=True để lấy giá trị tính toán thay vì công thức
    - Ô gộp: điền ô đầu, không lặp lại
    - Tối ưu số thập phân và ngày tháng
    - Bỏ qua biểu đồ và ảnh
    """
    ext = path.suffix.lower()
    export_mode = settings.get("excel_export_mode", "auto")
    auto_threshold = settings.get("excel_auto_threshold", 50)
    skip_hidden = settings.get("excel_skip_hidden_sheets", True)
    limit_rows = settings.get("excel_limit_rows", 0)
    compact_numbers = settings.get("excel_compact_numbers", True)
    format_dates = settings.get("excel_format_dates", True)

    # Xử lý riêng cho file CSV
    if ext == ".csv":
        return _convert_csv_file(path, export_mode, auto_threshold, limit_rows, compact_numbers, format_dates)

    # Xử lý .xlsx, .xlsm, .xls
    sections: List[str] = []

    try:
        # data_only=True giúp lấy giá trị đã tính toán của công thức thay vì chuỗi '=SUM(...)'
        wb = openpyxl.load_workbook(str(path), data_only=True, read_only=False)
    except Exception as e:
        log_warning(f"openpyxl không đọc được {path.name}, thử fallback: {e}")
        return _convert_excel_with_pandas_fallback(path, settings)

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]

        # Bỏ qua sheet ẩn nếu được bật
        if skip_hidden and sheet.sheet_state != "visible":
            log_debug(f"Bỏ qua sheet ẩn: {sheet_name}")
            continue

        # Đọc dữ liệu các ô
        # Trong openpyxl, ô gộp merged cell tự động chỉ có giá trị ở ô đầu, các ô còn lại có value là None
        raw_rows: List[List[str]] = []
        row_counter = 0

        for row in sheet.iter_rows(values_only=True):
            formatted_row = [
                format_cell_value(cell, compact_numbers=compact_numbers, format_dates=format_dates)
                for cell in row
            ]
            # Nếu hàng có ít nhất một ô có dữ liệu thì ghi nhận
            if any(c != "" for c in formatted_row):
                raw_rows.append(formatted_row)
                row_counter += 1
                if limit_rows > 0 and row_counter >= limit_rows:
                    break

        # Làm sạch hàng rỗng, cột rỗng
        cleaned_grid = clean_sheet_grid(raw_rows)
        if not cleaned_grid:
            # Sheet rỗng hoàn toàn
            continue

        sheet_md = f"## {sheet_name}\n\n"

        # Quyết định kiểu xuất: Markdown hay CSV
        num_data_rows = len(cleaned_grid)
        use_csv = False
        if export_mode == "csv":
            use_csv = True
        elif export_mode == "auto":
            use_csv = num_data_rows > auto_threshold
        else:
            use_csv = False

        if use_csv:
            sheet_md += export_as_csv_block(cleaned_grid)
        else:
            sheet_md += export_as_markdown_table(cleaned_grid)

        if limit_rows > 0 and len(raw_rows) >= limit_rows:
            sheet_md += f"\n*(Đã giới hạn hiển thị {limit_rows} dòng đầu của sheet)*\n\n"

        sections.append(sheet_md)

    wb.close()

    if not sections:
        return "*(Bảng tính rỗng hoặc không có dữ liệu)*\n"

    return "\n\n".join(sections)

def _convert_csv_file(
    path: Path,
    export_mode: str,
    auto_threshold: int,
    limit_rows: int,
    compact_numbers: bool,
    format_dates: bool
) -> str:
    """Xử lý file .csv với tự động nhận diện bảng mã (utf-8, utf-8-sig, cp1258)."""
    encodings = ["utf-8-sig", "utf-8", "cp1258", "latin-1"]
    raw_rows: List[List[str]] = []

    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                reader = csv.reader(f)
                row_cnt = 0
                for row in reader:
                    formatted_row = [
                        format_cell_value(c, compact_numbers=compact_numbers, format_dates=format_dates)
                        for c in row
                    ]
                    if any(c != "" for c in formatted_row):
                        raw_rows.append(formatted_row)
                        row_cnt += 1
                        if limit_rows > 0 and row_cnt >= limit_rows:
                            break
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise RuntimeError(f"Không thể đọc file CSV: {e}")

    cleaned_grid = clean_sheet_grid(raw_rows)
    if not cleaned_grid:
        return "*(File CSV rỗng)*\n"

    title = f"## {path.stem}\n\n"
    use_csv = False
    if export_mode == "csv":
        use_csv = True
    elif export_mode == "auto":
        use_csv = len(cleaned_grid) > auto_threshold
    else:
        use_csv = False

    if use_csv:
        content = export_as_csv_block(cleaned_grid)
    else:
        content = export_as_markdown_table(cleaned_grid)

    limit_note = ""
    if limit_rows > 0 and len(raw_rows) >= limit_rows:
        limit_note = f"\n*(Đã giới hạn hiển thị {limit_rows} dòng đầu)*\n"

    return title + content + limit_note

def _convert_excel_with_pandas_fallback(path: Path, settings: Dict[str, Any]) -> str:
    """Fallback dùng pandas nếu openpyxl gặp định dạng đặc biệt hoặc file .xls cũ."""
    try:
        import pandas as pd
        excel_file = pd.ExcelFile(str(path))
        sections = []
        export_mode = settings.get("excel_export_mode", "auto")
        auto_threshold = settings.get("excel_auto_threshold", 50)
        limit_rows = settings.get("excel_limit_rows", 0)

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=limit_rows if limit_rows > 0 else None)
            # Xóa các dòng/cột hoàn toàn NaN
            df = df.dropna(how="all").dropna(axis=1, how="all")
            if df.empty:
                continue

            # Chuyển thành danh sách chuỗi
            headers = [str(c) for c in df.columns]
            data_rows = df.fillna("").astype(str).values.tolist()
            grid = [headers] + data_rows

            cleaned_grid = clean_sheet_grid(grid)
            if not cleaned_grid:
                continue

            sheet_md = f"## {sheet_name}\n\n"
            use_csv = (export_mode == "csv") or (export_mode == "auto" and len(cleaned_grid) > auto_threshold)
            if use_csv:
                sheet_md += export_as_csv_block(cleaned_grid)
            else:
                sheet_md += export_as_markdown_table(cleaned_grid)
            sections.append(sheet_md)

        return "\n\n".join(sections)
    except Exception as e:
        raise RuntimeError(f"Lỗi khi đọc file Excel: {e}")
