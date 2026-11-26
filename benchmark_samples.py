from pathlib import Path
from app.converter import convert_single_file
from app.settings import settings_manager

def run_benchmark():
    samples_dir = Path(__file__).parent / "samples"
    sample_files = [
        "sample_multi_sheet.xlsx",
        "sample_large_5000.xlsx",
        "sample_document.docx",
        "sample_text.pdf",
        "sample_scanned.pdf",
        "sample_presentation.pptx"
    ]

    settings = settings_manager.get_all()
    # Thư mục kết quả trong samples/output
    out_dir = str(samples_dir / "output")
    settings["output_dir"] = out_dir

    print("\n" + "="*95)
    print(f"{'TÊN FILE MẪU':<28} | {'LOẠI':<6} | {'DUNG LƯỢNG':<10} | {'TRƯỚC':<10} | {'SAU':<10} | {'GIẢM (%)':<9} | {'TRẠNG THÁI'}")
    print("="*95)

    total_before = 0
    total_after = 0

    for fname in sample_files:
        fpath = samples_dir / fname
        if not fpath.exists():
            print(f"{fname:<28} | Không tìm thấy")
            continue

        size_kb = f"{fpath.stat().st_size / 1024:.1f} KB"
        ext = fpath.suffix.upper().replace(".", "")

        res = convert_single_file(str(fpath), settings=settings)
        if res.success:
            total_before += res.tokens_before
            total_after += res.tokens_after
            status = "✅ Thành công"
            tb = f"{res.tokens_before:,}"
            ta = f"{res.tokens_after:,}"
            red = f"-{res.reduction_pct:.1f}%"
        else:
            status = f"❌ {res.error_message[:25]}"
            tb = "-"
            ta = "-"
            red = "-"

        print(f"{fname:<28} | {ext:<6} | {size_kb:<10} | {tb:<10} | {ta:<10} | {red:<9} | {status}")

    print("="*95)
    total_red = 0.0
    if total_before > 0:
        total_red = ((total_before - total_after) / total_before) * 100.0
    print(f"{'TỔNG CỘNG TOÀN BỘ':<28} | ALL    | -          | {total_before:<10,}| {total_after:<10,}| -{total_red:.1f}%    |")
    print("="*95 + "\n")

if __name__ == "__main__":
    run_benchmark()
