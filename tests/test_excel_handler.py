import datetime
from pathlib import Path
import openpyxl
import pytest

from app.excel_handler import (
    clean_sheet_grid,
    convert_excel_file,
    export_as_csv_block,
    export_as_markdown_table,
    format_cell_value,
)

def test_format_cell_value():
    assert format_cell_value(None) == ""
    assert format_cell_value("NaN") == ""
    assert format_cell_value("Unnamed: 1") == ""
    assert format_cell_value(1.0) == "1"
    assert format_cell_value(123.450000) == "123.45"
    assert format_cell_value(datetime.date(2026, 11, 26)) == "2026-11-26"
    assert format_cell_value("Dòng 1\nDòng 2") == "Dòng 1 Dòng 2"

def test_clean_sheet_grid():
    raw_rows = [
        ["Tên", "Tuổi", ""],
        ["", "", ""],          # Hàng rỗng hoàn toàn
        ["An", "25", ""],
        ["Bình", "30", ""]      # Cột 3 rỗng hoàn toàn
    ]
    cleaned = clean_sheet_grid(raw_rows)
    assert len(cleaned) == 3
    assert len(cleaned[0]) == 2
    assert cleaned[0] == ["Tên", "Tuổi"]
    assert cleaned[1] == ["An", "25"]
    assert cleaned[2] == ["Bình", "30"]

def test_export_modes():
    grid = [
        ["Mã", "Tên sản phẩm", "Đơn giá"],
        ["SP01", "Bút bi", "5000"],
        ["SP02", "Vở kẻ ngang", "12000"]
    ]
    md_table = export_as_markdown_table(grid)
    assert "| Mã | Tên sản phẩm | Đơn giá |" in md_table
    assert "| --- | --- | --- |" in md_table

    csv_block = export_as_csv_block(grid)
    assert "```csv" in csv_block
    assert "SP01,Bút bi,5000" in csv_block

def test_convert_excel_file(tmp_path: Path):
    excel_path = tmp_path / "test_sample.xlsx"
    wb = openpyxl.Workbook()

    # Sheet 1: Dữ liệu chính + ô gộp + công thức
    ws1 = wb.active
    ws1.title = "DoanhThu"
    ws1["A1"] = "Báo cáo doanh thu"
    ws1.merge_cells("A1:B1")  # Ô gộp

    ws1["A2"] = "Tháng"
    ws1["B2"] = "Số tiền"
    ws1["A3"] = "Tháng 1"
    ws1["B3"] = 1000
    ws1["A4"] = "Tháng 2"
    ws1["B4"] = 2000
    ws1["A5"] = "Tổng cộng"
    ws1["B5"] = 3000  # Giả lập giá trị công thức đã tính

    # Sheet 2: Sheet ẩn
    ws2 = wb.create_sheet(title="DuLieuBiAn")
    ws2["A1"] = "Dữ liệu bí mật"
    ws2.sheet_state = "hidden"

    wb.save(str(excel_path))
    wb.close()

    # 1. Chuyển đổi bỏ qua sheet ẩn
    settings = {
        "excel_export_mode": "markdown",
        "excel_skip_hidden_sheets": True,
        "excel_auto_threshold": 50,
        "excel_limit_rows": 0,
        "excel_compact_numbers": True,
        "excel_format_dates": True
    }
    result_md = convert_excel_file(excel_path, settings)
    assert "## DoanhThu" in result_md
    assert "DuLieuBiAn" not in result_md
    assert "Báo cáo doanh thu" in result_md
    assert "3000" in result_md

    # 2. Chuyển đổi dạng CSV
    settings_csv = settings.copy()
    settings_csv["excel_export_mode"] = "csv"
    result_csv = convert_excel_file(excel_path, settings_csv)
    assert "```csv" in result_csv

    # 3. Giới hạn dòng (limit_rows = 3)
    settings_limit = settings.copy()
    settings_limit["excel_limit_rows"] = 3
    result_limit = convert_excel_file(excel_path, settings_limit)
    assert "giới hạn hiển thị" in result_limit
