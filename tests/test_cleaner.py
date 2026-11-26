import pytest
from app.cleaner import (
    clean_markdown,
    collapse_whitespace_and_newlines,
    remove_base64_images,
    remove_empty_table_rows_cols,
    remove_nan_unnamed,
    remove_repeated_headers_footers,
    shorten_divider_lines,
    strip_markdown_emphasis,
)

def test_remove_nan_unnamed():
    text = "| Tên | Giá trị | Unnamed: 2 |\n| --- | --- | --- |\n| A | NaN | nan |\n| B | None | null |"
    result = remove_nan_unnamed(text)
    assert "NaN" not in result
    assert "nan" not in result
    assert "Unnamed: 2" not in result
    assert "None" not in result

def test_remove_empty_table_rows_cols():
    # Bảng có 1 hàng rỗng và 1 cột rỗng hoàn toàn ở cột thứ 3
    table = (
        "| Header1 | Header2 | Header3 |\n"
        "| --- | --- | --- |\n"
        "| Val1 | Val2 | |\n"
        "| | | |\n"
        "| Val3 | Val4 | |"
    )
    result = remove_empty_table_rows_cols(table)
    # Hàng rỗng hoàn toàn phải biến mất
    assert "| | | |" not in result
    # Cột 3 rỗng hoàn toàn phải biến mất
    assert "Header3" not in result
    assert "| Header1 | Header2 |" in result
    assert "| Val1 | Val2 |" in result
    assert "| Val3 | Val4 |" in result

def test_collapse_whitespace_and_newlines():
    text = "Dòng 1    có   nhiều    khoảng  trắng.\n\n\n\n\nDòng 2 sau nhiều dòng trống."
    result = collapse_whitespace_and_newlines(text)
    # Không còn 3 dòng trống liên tiếp
    assert "\n\n\n" not in result
    # Khoảng trắng thừa được gộp
    assert "Dòng 1 có nhiều khoảng trắng." in result

def test_shorten_divider_lines():
    text = "Tiêu đề\n-----------------------------\nNội dung\n===================\nKết thúc"
    result = shorten_divider_lines(text)
    assert "-----------------------------" not in result
    assert "===================" not in result
    assert "---\nNội dung\n---\nKết thúc" in result

def test_remove_repeated_headers_footers():
    text = (
        "Trang 1 / 10\nNội dung bài viết 1\nTrang 1 / 10\n"
        "Nội dung bài viết 2\nTrang 1 / 10\nNội dung bài viết 3"
    )
    result = remove_repeated_headers_footers(text, min_repeats=3, max_length=80)
    assert "Trang 1 / 10" not in result
    assert "Nội dung bài viết 1" in result
    assert "Nội dung bài viết 2" in result

def test_remove_base64_images():
    text = "Trước ảnh\n![Hình ảnh](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==)\nSau ảnh"
    result = remove_base64_images(text)
    assert "data:image/png;base64" not in result
    assert "Trước ảnh" in result
    assert "Sau ảnh" in result

def test_strip_markdown_emphasis():
    text = "Đây là văn bản **rất quan trọng** và *chú thích nghiêng* cùng __đậm nữa__."
    result = strip_markdown_emphasis(text)
    assert "**" not in result
    assert "__" not in result
    assert "Đây là văn bản rất quan trọng và chú thích nghiêng cùng đậm nữa." == result

def test_clean_markdown_presets():
    dirty_text = (
        "| Cột 1 | Cột 2 | Cột 3 |\n"
        "| --- | --- | --- |\n"
        "| **A** | NaN | |\n"
        "| | | |\n"
        "| **B** | 100 | |\n\n\n\n"
        "--------------------\n"
        "Trang 1 / 10\nTrang 1 / 10\nTrang 1 / 10\n"
        "![icon](data:image/png;base64,ABCDEF123456)\n"
    )
    cleaned = clean_markdown(dirty_text, {
        "remove_nan_unnamed": True,
        "remove_empty_rows_cols": True,
        "collapse_whitespace": True,
        "shorten_dividers": True,
        "remove_repeated_headers": True,
        "remove_images": True,
        "strip_emphasis": True,
    })
    assert "NaN" not in cleaned
    assert "**A**" not in cleaned
    assert "| A |" in cleaned
    assert "data:image" not in cleaned
    assert "Trang 1 / 10" not in cleaned
    assert "\n\n\n" not in cleaned
