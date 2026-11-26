from pathlib import Path
import pytest

from app.converter import ConversionResult, merge_all_markdown_files, split_markdown_by_tokens

def test_split_markdown_by_tokens_no_table_split():
    # Tạo văn bản Markdown có tiêu đề và bảng
    section1 = "# Tiêu đề Phần 1\nĐây là nội dung phần 1 rất dài dòng và chi tiết.\n\n"
    table = (
        "| Cột 1 | Cột 2 |\n"
        "| --- | --- |\n"
        "| Dữ liệu 1 | Dữ liệu 2 |\n"
        "| Dữ liệu 3 | Dữ liệu 4 |\n\n"
    )
    section2 = "# Tiêu đề Phần 2\nĐây là nội dung phần 2 tiếp theo cũng rất dài.\n"
    full_text = section1 + table + section2

    # Đặt ngưỡng token nhỏ để buộc phải chia phần
    chunks = split_markdown_by_tokens(full_text, max_tokens=25)
    assert len(chunks) >= 2

    # Kiểm tra không chunk nào có bảng bị đứt rời dòng header và dòng dữ liệu
    for c in chunks:
        if "| Cột 1 |" in c:
            assert "| Dữ liệu 1 |" in c
            assert "| Dữ liệu 3 |" in c

def test_split_markdown_code_block_safety():
    code_block = (
        "# Phần Code\n"
        "```python\n"
        "def hello():\n"
        "    print('Hello world!')\n"
        "    return True\n"
        "```\n\n"
    )
    section2 = "# Phần Sau\nNội dung sau khối mã nguồn."
    full_text = code_block + section2

    chunks = split_markdown_by_tokens(full_text, max_tokens=20)
    for c in chunks:
        # Nếu có mở ``` thì phải có đóng ``` trong cùng chunk đó
        if "```python" in c:
            assert c.count("```") % 2 == 0

def test_merge_all_markdown_files(tmp_path: Path):
    r1 = ConversionResult(
        file_path=str(tmp_path / "bao_cao.docx"),
        success=True,
        cleaned_markdown="## Nội dung báo cáo quý 1",
        tokens_before=50,
        tokens_after=40
    )
    r2 = ConversionResult(
        file_path=str(tmp_path / "bang_luong.xlsx"),
        success=True,
        cleaned_markdown="## Bảng lương nhân viên",
        tokens_before=100,
        tokens_after=80
    )

    out_file = merge_all_markdown_files([r1, r2], output_dir=str(tmp_path))
    assert out_file is not None
    assert Path(out_file).exists()

    content = Path(out_file).read_text(encoding="utf-8")
    assert "# Nguồn: bao_cao.docx" in content
    assert "## Nội dung báo cáo quý 1" in content
    assert "# Nguồn: bang_luong.xlsx" in content
    assert "## Bảng lương nhân viên" in content
    assert "---" in content
