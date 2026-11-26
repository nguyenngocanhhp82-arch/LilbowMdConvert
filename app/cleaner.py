import re
from collections import Counter
from typing import Dict, List, Optional

def remove_nan_unnamed(text: str) -> str:
    """
    Xóa các giá trị 'NaN', 'nan', 'None', 'null', 'Unnamed: n' khỏi bảng và văn bản.
    Ví dụ: '| NaN | Unnamed: 1 |' -> '| | |'
    """
    if not text:
        return ""

    # Xóa Unnamed: số
    text = re.sub(r'Unnamed:\s*\d+', '', text)

    # Xóa NaN, nan, None, null đứng độc lập hoặc trong ô bảng
    # Xử lý trong ô bảng: | NaN | hoặc | nan |
    text = re.sub(r'\|\s*(?:NaN|nan|None|null|NULL)\s*\|', '| |', text)
    # Xử lý giữa 2 dấu gạch: | NaN
    text = re.sub(r'\|\s*(?:NaN|nan|None|null|NULL)\s*(?=\|)', '| ', text)

    # Xử lý từ độc lập ngoài bảng nếu có
    text = re.sub(r'\b(?:NaN|nan)\b', '', text)

    return text

def remove_empty_table_rows_cols(text: str) -> str:
    """
    Xóa hàng bảng rỗng hoàn toàn và cột bảng rỗng hoàn toàn trong Markdown table.
    """
    if not text or "|" not in text:
        return text

    lines = text.split("\n")
    output_lines: List[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        # Nhận diện dòng bảng Markdown
        if line.strip().startswith("|") and line.strip().endswith("|"):
            table_lines: List[str] = []
            while i < n and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            # Xử lý bảng vừa thu thập
            cleaned_table = _process_single_markdown_table(table_lines)
            output_lines.extend(cleaned_table)
        else:
            output_lines.append(line)
            i += 1

    return "\n".join(output_lines)

def _process_single_markdown_table(table_lines: List[str]) -> List[str]:
    """Hỗ trợ làm sạch 1 bảng Markdown cụ thể."""
    if len(table_lines) < 2:
        return table_lines

    # Phân tích các hàng thành danh sách ô
    parsed_rows: List[List[str]] = []
    is_delimiter_row: List[bool] = []

    for r in table_lines:
        # Bỏ dấu | ở đầu và cuối
        inner = r.strip()
        if inner.startswith("|"):
            inner = inner[1:]
        if inner.endswith("|"):
            inner = inner[:-1]
        cells = [c.strip() for c in inner.split("|")]

        # Kiểm tra xem có phải dòng phân cách không (ví dụ: :---, ---)
        is_delim = all(re.match(r"^:?-+:?$", c) for c in cells if c) and any(c for c in cells)
        parsed_rows.append(cells)
        is_delimiter_row.append(is_delim)

    if not parsed_rows:
        return []

    # 1. Xóa các hàng rỗng hoàn toàn (trừ hàng phân cách)
    kept_rows: List[List[str]] = []
    kept_is_delim: List[bool] = []

    for cells, is_delim in zip(parsed_rows, is_delimiter_row):
        if is_delim:
            kept_rows.append(cells)
            kept_is_delim.append(is_delim)
        else:
            # Hàng có ít nhất một ô có nội dung
            if any(cell != "" for cell in cells):
                kept_rows.append(cells)
                kept_is_delim.append(is_delim)

    if not kept_rows or len(kept_rows) <= 1:
        # Bảng chỉ có tiêu đề hoặc rỗng hoàn toàn
        return []

    # Chuẩn hóa số lượng cột cho đều nhau
    max_cols = max(len(r) for r in kept_rows)
    for r in kept_rows:
        while len(r) < max_cols:
            r.append("")

    # 2. Tìm các cột rỗng hoàn toàn
    # Xác định dòng phân cách header (---)
    delim_idx = -1
    for idx, is_d in enumerate(kept_is_delim):
        if is_d:
            delim_idx = idx
            break

    empty_col_indices = set()
    if delim_idx != -1 and delim_idx + 1 < len(kept_rows):
        # Các dòng dữ liệu thực sự nằm sau dòng phân cách
        actual_data_rows = kept_rows[delim_idx + 1:]
        for col_idx in range(max_cols):
            if all(row[col_idx] == "" for row in actual_data_rows):
                empty_col_indices.add(col_idx)
    else:
        # Nếu không có dòng phân cách, kiểm tra tất cả các hàng
        for col_idx in range(max_cols):
            if all(row[col_idx] == "" for row in kept_rows):
                empty_col_indices.add(col_idx)

    # 3. Loại bỏ các cột rỗng này
    result_table: List[str] = []
    for cells, is_delim in zip(kept_rows, kept_is_delim):
        filtered_cells = [cells[c_idx] for c_idx in range(max_cols) if c_idx not in empty_col_indices]
        if not filtered_cells:
            continue
        if is_delim:
            # Chuẩn hóa ngắn gọn cho dòng gạch phân cách
            delim_str = "| " + " | ".join("---" for _ in filtered_cells) + " |"
            result_table.append(delim_str)
        else:
            row_str = "| " + " | ".join(filtered_cells) + " |"
            result_table.append(row_str)

    return result_table

def collapse_whitespace_and_newlines(text: str) -> str:
    """
    Gộp khoảng trắng thừa và các dòng trống liên tiếp.
    Chỉ giữ tối đa 1 dòng trống (tức 2 ký tự xuống dòng liên tiếp).
    """
    if not text:
        return ""

    lines = text.split("\n")
    cleaned_lines = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            cleaned_lines.append(line.rstrip())
            continue

        if in_code_block:
            cleaned_lines.append(line)
        else:
            # Gộp nhiều khoảng trắng liên tiếp trong văn bản thông thường (trừ dòng bảng)
            if not stripped.startswith("|"):
                line = re.sub(r'[ \t]{2,}', ' ', line)
            cleaned_lines.append(line.rstrip())

    # Gộp nhiều hơn 2 dòng trống liên tiếp thành tối đa 1 dòng trống
    result = "\n".join(cleaned_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip() + "\n"

def shorten_divider_lines(text: str) -> str:
    """
    Rút gọn các dòng phân cách dài như '--------------' thành '---'
    và chuẩn hóa các ô phân cách trong bảng.
    """
    if not text:
        return ""

    # Dòng phân cách độc lập: ---, ***, ___ dài hơn 3 ký tự
    text = re.sub(r'^[ \t]*[-*_]{4,}[ \t]*$', '---', text, flags=re.MULTILINE)
    # Dòng dấu bằng: =====
    text = re.sub(r'^[ \t]*={3,}[ \t]*$', '---', text, flags=re.MULTILINE)

    # Rút gọn các dấu gạch phân cách trong bảng: | -------- | thành | --- |
    def replace_table_delim(match):
        inner = match.group(0)
        # Thay thế các chuỗi gạch dài bên trong ô
        shortened = re.sub(r':?-{3,}:?', '---', inner)
        return shortened

    text = re.sub(r'^\|[\s\-:|]+\|$', replace_table_delim, text, flags=re.MULTILINE)

    return text

def remove_repeated_headers_footers(text: str, min_repeats: int = 3, max_length: int = 80) -> str:
    """
    Xóa header/footer/số trang lặp lại (dòng xuất hiện từ 3 lần trở lên và ngắn dưới 80 ký tự).
    Ví dụ: 'Trang 1', 'Bản quyền thuộc về...', 'Tài liệu mật nội bộ'
    """
    if not text:
        return ""

    lines = text.split("\n")
    # Đếm tần suất các dòng ngắn không phải rỗng, không phải Markdown table/header/code
    candidate_lines = []
    for line in lines:
        s = line.strip()
        if 0 < len(s) < max_length:
            # Bỏ qua các dòng cú pháp Markdown thông dụng
            if s.startswith("#") or s.startswith("|") or s.startswith("```") or s == "---":
                continue
            # Bỏ qua các mục danh sách ngắn nếu có
            if re.match(r'^[-*+]\s+', s) or re.match(r'^\d+\.\s+', s):
                continue
            candidate_lines.append(s)

    counts = Counter(candidate_lines)
    repeated_patterns = {line for line, cnt in counts.items() if cnt >= min_repeats}

    # Bổ sung regex nhận diện số trang phổ biến: 'Trang 1', 'Trang 1 / 10', 'Page 1 of 5'
    page_regex = re.compile(r'^(?:Trang|Page)\s+\d+(?:\s*(?:/|của|of)\s*\d+)?$', re.IGNORECASE)

    output_lines = []
    for line in lines:
        s = line.strip()
        if s in repeated_patterns or (page_regex.match(s) and len(s) < 30):
            continue
        output_lines.append(line)

    return "\n".join(output_lines)

def remove_base64_images(text: str) -> str:
    """
    Xóa link ảnh nhúng dạng base64 (data:image/...;base64,...) để tiết kiệm token lớn.
    """
    if not text:
        return ""

    # Xóa ảnh markdown dạng ![](data:image/...)
    text = re.sub(r'!\[.*?\]\(data:image\/[a-zA-Z0-9\+\-\.]+;base64,[a-zA-Z0-9\+\/\=\s]+\)', '', text)

    # Xóa thẻ HTML <img> chứa base64
    text = re.sub(r'<img[^>]*src=["\']data:image\/[^"\']+["\'][^>]*>', '', text)

    # Xóa ảnh markdown dạng thông thường nếu người dùng muốn bỏ ảnh hoàn toàn
    text = re.sub(r'!\[.*?\]\([^\)]+\)', '', text)

    return text

def strip_markdown_emphasis(text: str) -> str:
    """
    Tùy chọn: bỏ định dạng nhấn mạnh **đậm**, *nghiêng*, __đậm__, _nghiêng_ để văn bản nhẹ hơn.
    """
    if not text:
        return ""

    # Bỏ **đậm** và __đậm__
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)

    # Bỏ *nghiêng* và _nghiêng_ (cẩn thận không xóa dấu bullet point ở đầu dòng)
    text = re.sub(r'(?<!\*)\*([^\s\*].*?[^\s\*])\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_([^\s_].*?[^\s_])_(?!_)', r'\1', text)

    return text

def clean_markdown(text: str, options: Optional[Dict[str, bool]] = None) -> str:
    """
    Hàm tổng hợp làm sạch Markdown theo danh sách tùy chọn được bật/tắt.
    """
    if not text:
        return ""

    if options is None:
        options = {
            "remove_nan_unnamed": True,
            "remove_empty_rows_cols": True,
            "collapse_whitespace": True,
            "shorten_dividers": True,
            "remove_repeated_headers": True,
            "remove_images": True,
            "strip_emphasis": False,
        }

    # 1. Xóa ảnh base64
    if options.get("remove_images", True):
        text = remove_base64_images(text)

    # 2. Xóa NaN, Unnamed
    if options.get("remove_nan_unnamed", True):
        text = remove_nan_unnamed(text)

    # 3. Xóa hàng/cột bảng rỗng hoàn toàn
    if options.get("remove_empty_rows_cols", True):
        text = remove_empty_table_rows_cols(text)

    # 4. Rút gọn đường phân cách
    if options.get("shorten_dividers", True):
        text = shorten_divider_lines(text)

    # 5. Xóa header/footer/số trang lặp lại
    if options.get("remove_repeated_headers", True):
        text = remove_repeated_headers_footers(text)

    # 6. Bỏ định dạng nhấn mạnh đậm/nghiêng (tùy chọn)
    if options.get("strip_emphasis", False):
        text = strip_markdown_emphasis(text)

    # 7. Gộp khoảng trắng thừa và dòng trống liên tiếp (chạy cuối cùng)
    if options.get("collapse_whitespace", True):
        text = collapse_whitespace_and_newlines(text)

    return text
