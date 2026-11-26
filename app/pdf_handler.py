import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image
import pymupdf
import pytesseract

from app.logger import log_debug, log_error, log_info, log_warning

def find_tesseract_cmd() -> Optional[str]:
    """Tìm đường dẫn tesseract trên Windows hoặc Linux."""
    # 1. Kiểm tra PATH hiện tại
    cmd = shutil.which("tesseract")
    if cmd:
        return cmd

    # 2. Kiểm tra các thư mục mặc định trên Windows
    if sys.platform == "win32":
        standard_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for p in standard_paths:
            if os.path.isfile(p):
                return p

    return None

def is_tesseract_available() -> Tuple[bool, Optional[str]]:
    """Kiểm tra xem Tesseract đã được cài đặt và sẵn sàng chưa."""
    cmd = find_tesseract_cmd()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
        return True, cmd
    return False, None

def unwrap_pdf_lines(text: str) -> str:
    """
    Gộp các dòng bị ngắt giữa chừng do định dạng ngắt dòng cứng của PDF
    thành đoạn văn liền mạch, trong khi giữ nguyên tiêu đề, bảng, danh sách.
    """
    if not text:
        return ""

    lines = text.split("\n")
    unwrapped_lines: List[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].rstrip()
        if not line:
            unwrapped_lines.append("")
            i += 1
            continue

        # Các dòng đặc biệt không được gộp bừa bãi
        if (
            line.startswith("#")
            or line.startswith("|")
            or line.startswith("- ")
            or line.startswith("* ")
            or line.startswith("+ ")
            or re.match(r"^\d+\.\s+", line)
            or line.startswith("<!--")
            or line.endswith((".", "!", "?", ":", ";", "---", "```", '"', "”"))
        ):
            unwrapped_lines.append(line)
            i += 1
            continue

        # Kiểm tra dòng tiếp theo
        if i + 1 < n:
            next_line = lines[i + 1].strip()
            # Dòng tiếp theo là văn bản thường thì gộp vào
            if (
                next_line
                and not next_line.startswith("#")
                and not next_line.startswith("|")
                and not next_line.startswith(("- ", "* ", "+ "))
                and not re.match(r"^\d+\.\s+", next_line)
                and not next_line.startswith("<!--")
            ):
                # Nối tiếp với dòng tiếp theo
                lines[i + 1] = line + " " + next_line
                i += 1
                continue

        unwrapped_lines.append(line)
        i += 1

    return "\n".join(unwrapped_lines)

def convert_pdf_file(
    path: Path,
    settings: Dict[str, Any],
    cancel_check: Optional[Callable[[], bool]] = None
) -> str:
    """
    Chuyển đổi file PDF sang Markdown:
    - Thử trích xuất text thông thường trước
    - Nếu trang ít chữ (< 20 ký tự), coi là trang scan và chạy OCR
    - Gộp dòng ngắt giữa chừng thành đoạn văn liền mạch
    - Đánh dấu trang <!-- trang X --> (tùy chọn)
    - Nếu máy chưa có Tesseract, báo thông báo tiếng Việt rõ ràng và vẫn chuyển các trang có text.
    """
    enable_ocr = settings.get("enable_ocr", True)
    ocr_lang = settings.get("ocr_lang", "vie+eng")
    ocr_dpi = settings.get("ocr_dpi", 300)
    page_markers = settings.get("pdf_page_markers", True)

    try:
        doc = pymupdf.open(str(path))
    except Exception as e:
        err_msg = str(e)
        if "password" in err_msg.lower() or "encrypted" in err_msg.lower():
            raise RuntimeError("File có mật khẩu bảo vệ, chưa hỗ trợ.")
        raise RuntimeError(f"Không thể mở file PDF: {e}")

    # Kiểm tra mã hóa mật khẩu
    if doc.is_encrypted or doc.needs_pass:
        doc.close()
        raise RuntimeError("File có mật khẩu bảo vệ, chưa hỗ trợ.")

    pages_output: List[str] = []
    tesseract_ok, tesseract_path = is_tesseract_available()
    tesseract_warning_shown = False

    for page_num in range(len(doc)):
        if cancel_check and cancel_check():
            doc.close()
            raise RuntimeError("Người dùng đã hủy tiến trình.")

        page = doc[page_num]
        display_page_num = page_num + 1

        # 1. Thử trích xuất text trực tiếp
        page_text = page.get_text("text").strip()

        # 2. Kiểm tra nếu trang scan (< 20 ký tự text)
        is_scanned_page = len(page_text) < 20

        if is_scanned_page and enable_ocr:
            log_debug(f"Trang {display_page_num} có ít hơn 20 ký tự, chạy OCR...")
            if tesseract_ok:
                try:
                    # Trích xuất ảnh độ phân giải cao 300 DPI
                    pix = page.get_pixmap(dpi=ocr_dpi)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    # Chạy Tesseract OCR vie+eng
                    try:
                        ocr_result = pytesseract.image_to_string(img, lang=ocr_lang)
                    except Exception:
                        # Thử lại với ngôn ngữ tiếng Anh hoặc mặc định nếu thiếu gói 'vie'
                        ocr_result = pytesseract.image_to_string(img, lang="eng")

                    ocr_result = ocr_result.strip()
                    if ocr_result:
                        page_text = ocr_result
                except Exception as ocr_err:
                    log_warning(f"Lỗi khi OCR trang {display_page_num}: {ocr_err}")
            else:
                if not tesseract_warning_shown:
                    log_warning("Máy chưa cài đặt Tesseract OCR. Bỏ qua OCR cho các trang scan.")
                    tesseract_warning_shown = True
                page_text = (
                    "*(Trang này là bản scan nhưng máy tính chưa cài đặt Tesseract OCR. "
                    "Vui lòng cài đặt Tesseract kèm gói ngôn ngữ 'vie + eng' theo hướng dẫn để nhận diện văn bản.)*"
                )

        # 3. Gộp dòng bị ngắt giữa chừng
        page_text = unwrap_pdf_lines(page_text)

        # 4. Thêm đánh dấu trang nếu được bật
        if page_markers:
            page_text = f"<!-- trang {display_page_num} -->\n{page_text}"

        if page_text.strip():
            pages_output.append(page_text.strip())

    doc.close()

    if not pages_output:
        return "*(Tài liệu PDF rỗng hoặc không có nội dung chữ)*\n"

    return "\n\n".join(pages_output) + "\n"
