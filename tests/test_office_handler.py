from pathlib import Path
from docx import Document
from pptx import Presentation
from pptx.util import Inches
import pytest

from app.converter import _convert_office_file

def test_convert_docx(tmp_path: Path):
    doc_path = tmp_path / "test_doc.docx"
    doc = Document()
    doc.add_heading("Tiêu đề tài liệu Word", level=1)
    doc.add_paragraph("Đây là đoạn văn bản kiểm thử.")
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Cột A"
    table.rows[0].cells[1].text = "Cột B"
    table.rows[1].cells[0].text = "Dữ liệu 1"
    table.rows[1].cells[1].text = "Dữ liệu 2"
    doc.save(str(doc_path))

    settings = {"pptx_keep_notes": True}
    md_result = _convert_office_file(doc_path, ".docx", settings)
    assert "Tiêu đề tài liệu Word" in md_result
    assert "Đây là đoạn văn bản kiểm thử." in md_result
    assert "Cột A" in md_result
    assert "Dữ liệu 1" in md_result

def test_convert_pptx(tmp_path: Path):
    pptx_path = tmp_path / "test_slides.pptx"
    prs = Presentation()
    slide_layout = prs.slide_layouts[0]  # Title slide
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "Tiêu đề Slide 1"
    subtitle.text = "Nội dung slide kiểm thử"

    # Thêm ghi chú diễn giả
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = "Đây là ghi chú bí mật của diễn giả"

    prs.save(str(pptx_path))

    settings = {"pptx_keep_notes": True}
    md_result = _convert_office_file(pptx_path, ".pptx", settings)
    assert "Tiêu đề Slide 1" in md_result
    assert "Đây là ghi chú bí mật của diễn giả" in md_result
