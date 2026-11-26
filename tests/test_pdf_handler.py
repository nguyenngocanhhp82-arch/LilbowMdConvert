from pathlib import Path
import pymupdf
import pytest

from app.pdf_handler import convert_pdf_file, unwrap_pdf_lines

def test_unwrap_pdf_lines():
    text = (
        "Đây là một câu rất dài bị ngắt dòng ở\n"
        "giữa chừng do định dạng cột trong file PDF.\n"
        "Đây là câu thứ hai đã kết thúc.\n"
        "# Tiêu đề không được gộp\n"
        "- Mục danh sách 1\n"
        "- Mục danh sách 2\n"
        "| Cột 1 | Cột 2 |\n"
        "| --- | --- |\n"
        "| A | B |"
    )
    unwrapped = unwrap_pdf_lines(text)
    # Câu 1 và 2 được nối lại
    assert "Đây là một câu rất dài bị ngắt dòng ở giữa chừng do định dạng cột trong file PDF." in unwrapped
    # Tiêu đề và danh sách vẫn độc lập
    assert "# Tiêu đề không được gộp" in unwrapped
    assert "- Mục danh sách 1" in unwrapped
    assert "| Cột 1 | Cột 2 |" in unwrapped

def test_convert_pdf_file(tmp_path: Path):
    pdf_path = tmp_path / "sample_doc.pdf"

    # Tạo PDF mẫu 2 trang bằng pymupdf
    doc = pymupdf.open()

    # Trang 1: Text bình thường
    page1 = doc.new_page()
    page1.insert_text((50, 72), "Welcome to LilbowMdConvert document converter.\nThis is a standard PDF test line.")

    # Trang 2: Trang gần như rỗng (< 20 ký tự) để thử logic scan fallback
    page2 = doc.new_page()
    page2.insert_text((50, 72), "A")

    doc.save(str(pdf_path))
    doc.close()

    # Chạy chuyển đổi
    settings = {
        "enable_ocr": True,
        "ocr_lang": "vie+eng",
        "ocr_dpi": 300,
        "pdf_page_markers": True
    }

    result_md = convert_pdf_file(pdf_path, settings)
    assert "<!-- trang 1 -->" in result_md
    assert "Welcome to LilbowMdConvert document converter." in result_md
    assert "<!-- trang 2 -->" in result_md
