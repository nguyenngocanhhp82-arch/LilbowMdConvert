from pathlib import Path
import pytest
from app.converter import convert_single_file, extract_raw_markdown

def test_extract_raw_markdown(tmp_path: Path):
    sample_txt = tmp_path / "hello.csv"
    sample_txt.write_text("Tên,Tuổi,Chức Vụ\nNguyễn Văn An,28,Kỹ Sư\nTrần Thị Bình,30,Kế Toán", encoding="utf-8")

    settings = {"excel_export_mode": "markdown"}
    raw_md, tokens = extract_raw_markdown(sample_txt, settings)

    assert tokens > 0
    assert "Nguyễn Văn An" in raw_md
    assert "Kế Toán" in raw_md

def test_convert_single_file_with_precomputed(tmp_path: Path):
    sample_file = tmp_path / "test.csv"
    sample_file.write_text("A,B\n1,2", encoding="utf-8")

    precomputed_text = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    precomputed_tok = 15

    res = convert_single_file(
        str(sample_file),
        precomputed_raw_md=precomputed_text,
        precomputed_tokens=precomputed_tok
    )

    assert res.success is True
    assert res.tokens_before == 15
    assert res.tokens_after > 0
    assert len(res.output_paths) > 0
