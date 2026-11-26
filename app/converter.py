import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from markitdown import MarkItDown

from app.cleaner import clean_markdown
from app.logger import log_debug, log_error, log_info, log_warning
from app.settings import settings_manager
from app.tokens import calculate_reduction, count_tokens

SUPPORTED_EXTENSIONS = {
    ".xlsx", ".xls", ".xlsm", ".csv",
    ".docx", ".doc",
    ".pdf",
    ".pptx"
}

class ConversionResult:
    def __init__(
        self,
        file_path: str,
        success: bool,
        output_paths: Optional[List[str]] = None,
        raw_markdown: str = "",
        cleaned_markdown: str = "",
        tokens_before: int = 0,
        tokens_after: int = 0,
        reduction_pct: float = 0.0,
        error_message: str = ""
    ):
        self.file_path = file_path
        self.success = success
        self.output_paths = output_paths or []
        self.raw_markdown = raw_markdown
        self.cleaned_markdown = cleaned_markdown
        self.tokens_before = tokens_before
        self.tokens_after = tokens_after
        self.reduction_pct = reduction_pct
        self.error_message = error_message

def check_file_accessible(file_path: Path) -> Tuple[bool, str]:
    """Kiểm tra quyền truy cập file, phát hiện file bị khóa hoặc rỗng."""
    if not file_path.exists():
        return False, "File không tồn tại."
    if file_path.stat().st_size == 0:
        return False, "File rỗng (0 bytes), không có dữ liệu."

    # Thử mở để kiểm tra file có bị phần mềm khác (Word/Excel) khóa không
    try:
        with open(file_path, "rb") as f:
            _ = f.read(1024)
    except PermissionError:
        return False, "Hãy đóng file rồi thử lại (file đang được mở bởi ứng dụng khác)."
    except Exception as e:
        return False, f"Không thể đọc file: {str(e)}"

    return True, ""

def resolve_output_path(
    input_file: Path,
    custom_output_dir: Optional[str] = None,
    conflict_mode: str = "rename",
    suffix: str = "",
    part_index: Optional[int] = None
) -> Path:
    """
    Xác định đường dẫn lưu file đầu ra .md và xử lý xung đột tên file.
    """
    if custom_output_dir and custom_output_dir.strip():
        out_dir = Path(custom_output_dir.strip())
    else:
        out_dir = input_file.parent / "md_output"

    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = input_file.stem
    if part_index is not None:
        file_name = f"{base_name}{suffix}_part{part_index}.md"
    else:
        file_name = f"{base_name}{suffix}.md"

    target_path = out_dir / file_name

    if not target_path.exists():
        return target_path

    if conflict_mode == "overwrite":
        return target_path
    elif conflict_mode == "skip":
        return target_path
    elif conflict_mode == "rename":
        counter = 1
        while True:
            if part_index is not None:
                new_name = f"{base_name}{suffix}_part{part_index}_{counter}.md"
            else:
                new_name = f"{base_name}{suffix}_{counter}.md"
            new_path = out_dir / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    return target_path

def get_raw_baseline_tokens(path: Path) -> int:
    """
    Tính lượng token ban đầu của tài liệu nguyên bản (chưa qua tối ưu, lọc rác, nén bảng).
    Đây là mốc chuẩn (baseline) phản ánh đúng chi phí nếu người dùng nạp nguyên bản vào AI.
    """
    ext = path.suffix.lower()
    try:
        if ext in {".xlsx", ".xls", ".xlsm"}:
            # Đo lượng token nguyên bản của toàn bộ các sheet (kể cả sheet ẩn),
            # với định dạng bảng đầy đủ và dữ liệu thô
            import openpyxl
            wb = openpyxl.load_workbook(str(path), data_only=False, read_only=True)
            total_cells_text = []
            for sname in wb.sheetnames:
                total_cells_text.append(f"## {sname}")
                ws = wb[sname]
                for row in ws.iter_rows(values_only=True):
                    row_strs = [str(c) if c is not None else "" for c in row]
                    if any(c != "" for c in row_strs):
                        total_cells_text.append("| " + " | ".join(row_strs) + " |")
            wb.close()
            if total_cells_text:
                return count_tokens("\n".join(total_cells_text))
    except Exception:
        pass

    try:
        md_engine = MarkItDown()
        res = md_engine.convert(str(path))
        raw_text = res.text_content or ""
        return count_tokens(raw_text)
    except Exception:
        pass

    return 0

def extract_raw_markdown(
    path: Path,
    settings: Optional[Dict[str, Any]] = None,
    cancel_check: Optional[Callable[[], bool]] = None
) -> Tuple[str, int]:
    """
    Trích xuất văn bản của tài liệu và tính lượng token ban đầu chuẩn xác của tài liệu nguyên bản.
    Trả về: (optimized_raw_md, raw_baseline_tokens)
    """
    if settings is None:
        settings = settings_manager.get_all()

    # 1. Tính lượng token ban đầu chuẩn xác của tài liệu nguyên bản
    raw_baseline_tokens = get_raw_baseline_tokens(path)

    ext = path.suffix.lower()
    if ext in {".xlsx", ".xls", ".xlsm", ".csv"}:
        from app.excel_handler import convert_excel_file
        raw_md = convert_excel_file(path, settings)
    elif ext == ".pdf":
        from app.pdf_handler import convert_pdf_file
        raw_md = convert_pdf_file(path, settings, cancel_check=cancel_check)
    elif ext in {".docx", ".doc", ".pptx"}:
        raw_md = _convert_office_file(path, ext, settings)
    else:
        md_engine = MarkItDown()
        result = md_engine.convert(str(path))
        raw_md = result.text_content or ""

    if raw_baseline_tokens <= 0:
        raw_baseline_tokens = count_tokens(raw_md)

    return raw_md, raw_baseline_tokens

def convert_single_file(
    file_path: str,
    settings: Optional[Dict[str, Any]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    precomputed_raw_md: Optional[str] = None,
    precomputed_tokens: Optional[int] = None
) -> ConversionResult:
    """
    Chuyển đổi 1 file tài liệu sang Markdown và làm sạch để tối ưu token.
    Nếu đã có precomputed_raw_md từ bước thêm file, tái sử dụng để tăng tốc.
    """
    if settings is None:
        settings = settings_manager.get_all()

    path = Path(file_path).resolve()
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        return ConversionResult(
            file_path=str(path),
            success=False,
            error_message=f"Định dạng {ext} chưa được hỗ trợ."
        )

    # 1. Kiểm tra tính khả dụng của file
    accessible, reason = check_file_accessible(path)
    if not accessible:
        return ConversionResult(
            file_path=str(path),
            success=False,
            error_message=reason
        )

    if cancel_check and cancel_check():
        return ConversionResult(
            file_path=str(path),
            success=False,
            error_message="Người dùng đã hủy tiến trình."
        )

    raw_md = ""
    tokens_before = 0
    error_msg = ""

    try:
        if precomputed_raw_md is not None and precomputed_raw_md != "":
            raw_md = precomputed_raw_md
            tokens_before = precomputed_tokens if precomputed_tokens is not None and precomputed_tokens > 0 else get_raw_baseline_tokens(path)
        else:
            raw_md, tokens_before = extract_raw_markdown(path, settings, cancel_check=cancel_check)
    except Exception as e:
        log_error(f"Lỗi khi chuyển đổi file {path.name}: {e}", exc_info=True)
        # Bắt các thông điệp lỗi đặc thù và dịch sang tiếng Việt
        err_str = str(e)
        if "password" in err_str.lower() or "encrypted" in err_str.lower():
            error_msg = "File có mật khẩu bảo vệ, chưa hỗ trợ."
        elif "permission" in err_str.lower():
            error_msg = "Hãy đóng file rồi thử lại (file đang bị khóa)."
        else:
            error_msg = f"Lỗi chuyển đổi: {err_str}"

        return ConversionResult(
            file_path=str(path),
            success=False,
            error_message=error_msg
        )

    if cancel_check and cancel_check():
        return ConversionResult(
            file_path=str(path),
            success=False,
            error_message="Người dùng đã hủy tiến trình."
        )

    # Đảm bảo tokens_before phản ánh đúng lượng token nguyên bản
    if tokens_before <= 0:
        tokens_before = get_raw_baseline_tokens(path)
        if tokens_before <= 0:
            tokens_before = count_tokens(raw_md)

    # 4. Làm sạch bằng cleaner
    cleaner_rules = settings.get("cleaner_rules", {})
    cleaned_md = clean_markdown(raw_md, cleaner_rules)
    tokens_after = count_tokens(cleaned_md)
    reduction = calculate_reduction(tokens_before, tokens_after)

    # 5. Lưu ra file .md
    out_dir = settings.get("output_dir", "")
    conflict_mode = settings.get("name_conflict_mode", "rename")
    split_enabled = settings.get("split_enabled", False)
    split_limit = settings.get("split_token_limit", 30000)

    saved_paths: List[str] = []

    try:
        if split_enabled and tokens_after > split_limit:
            # Chia nhỏ file
            from app.converter import split_markdown_by_tokens
            chunks = split_markdown_by_tokens(cleaned_md, split_limit)
            for idx, chunk in enumerate(chunks, 1):
                part_path = resolve_output_path(
                    path,
                    custom_output_dir=out_dir,
                    conflict_mode=conflict_mode,
                    part_index=idx
                )
                with open(part_path, "w", encoding="utf-8") as f:
                    f.write(chunk)
                saved_paths.append(str(part_path))
        else:
            target_path = resolve_output_path(
                path,
                custom_output_dir=out_dir,
                conflict_mode=conflict_mode
            )
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(cleaned_md)
            saved_paths.append(str(target_path))

        log_info(f"Đã chuyển đổi thành công {path.name} -> {len(saved_paths)} file (.md). Tokens: {tokens_before} -> {tokens_after} (-{reduction}%)")
        return ConversionResult(
            file_path=str(path),
            success=True,
            output_paths=saved_paths,
            raw_markdown=raw_md,
            cleaned_markdown=cleaned_md,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            reduction_pct=reduction
        )
    except Exception as e:
        log_error(f"Lỗi khi ghi file đầu ra cho {path.name}: {e}", exc_info=True)
        return ConversionResult(
            file_path=str(path),
            success=False,
            error_message=f"Lỗi lưu file kết quả: {str(e)}"
        )

def _convert_office_file(path: Path, ext: str, settings: Dict[str, Any]) -> str:
    """Xử lý Word (.docx, .doc) và PowerPoint (.pptx)."""
    # Xử lý định dạng Word cũ .doc
    if ext == ".doc":
        converted_docx = _try_convert_legacy_office_file(path, "docx")
        if converted_docx and converted_docx.exists():
            path = converted_docx
            ext = ".docx"
        else:
            raise RuntimeError(
                "Định dạng .doc cũ yêu cầu cài đặt LibreOffice để chuyển tự động. "
                "Vui lòng lưu lại file thành .docx rồi thử lại."
            )

    # Chuyển đổi bằng MarkItDown
    md_engine = MarkItDown()
    result = md_engine.convert(str(path))
    content = result.text_content or ""

    # Với PowerPoint, nếu có tùy chọn giữ ghi chú diễn giả:
    if ext == ".pptx":
        if not settings.get("pptx_keep_notes", True):
            # Bỏ ghi chú diễn giả để tiết kiệm token tối đa
            content = re.sub(r'###\s*Notes:.*?(?=(?:<!--\s*Slide number:|\Z))', '', content, flags=re.DOTALL)
        else:
            # Nếu MarkItDown chưa có khối Notes thì fallback sang python-pptx để lấy
            if "### Notes:" not in content and "### Ghi chú:" not in content:
                try:
                    from pptx import Presentation
                    prs = Presentation(str(path))
                    slide_notes = []
                    has_any_notes = False
                    for idx, slide in enumerate(prs.slides, 1):
                        if slide.has_notes_slide:
                            notes_text = slide.notes_slide.notes_text_frame.text.strip()
                            if notes_text:
                                has_any_notes = True
                                slide_notes.append(f"### Ghi chú Slide {idx}\n{notes_text}")
                    if has_any_notes:
                        content += "\n\n## Ghi chú diễn giả (Speaker Notes)\n" + "\n\n".join(slide_notes)
                except Exception as e:
                    log_warning(f"Không thể đọc ghi chú PowerPoint {path.name}: {e}")

    return content

def _try_convert_legacy_office_file(path: Path, target_ext: str) -> Optional[Path]:
    """Thử dùng libreoffice hoặc soffice trên máy để chuyển file .doc/.xls cũ."""
    soffice_path = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice_path:
        return None
    try:
        import subprocess
        out_dir = path.parent
        cmd = [soffice_path, "--headless", "--convert-to", target_ext, str(path), "--outdir", str(out_dir)]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=True)
        converted = out_dir / f"{path.stem}.{target_ext}"
        if converted.exists():
            return converted
    except Exception:
        pass
    return None

def split_markdown_by_tokens(text: str, max_tokens: int = 30000) -> List[str]:
    """
    Chia nhỏ văn bản Markdown theo số token tối đa.
    Ưu tiên cắt tại ranh giới tiêu đề (#, ##, ###) hoặc sheet.
    Không bao giờ cắt ngang giữa bảng Markdown (|...|) hoặc giữa khối code (```...```).
    """
    total_tokens = count_tokens(text)
    if total_tokens <= max_tokens:
        return [text]

    lines = text.split("\n")
    chunks: List[str] = []
    current_chunk_lines: List[str] = []
    current_tokens = 0
    in_code_block = False

    for line in lines:
        stripped = line.strip()
        is_fence = stripped.startswith("```")
        is_table_line = stripped.startswith("|") and stripped.endswith("|")

        # Cắt an toàn khi không nằm trong code block và không nằm trong bảng
        is_safe_cut = (not in_code_block) and (not is_fence) and (not is_table_line)
        line_tokens = count_tokens(line + "\n")

        if current_chunk_lines and is_safe_cut and (current_tokens + line_tokens > max_tokens):
            chunks.append("\n".join(current_chunk_lines).strip() + "\n")
            current_chunk_lines = [line]
            current_tokens = line_tokens
        else:
            current_chunk_lines.append(line)
            current_tokens += line_tokens

        # Cập nhật trạng thái code block sau khi đã ghi nhận dòng
        if is_fence:
            in_code_block = not in_code_block

    if current_chunk_lines:
        chunks.append("\n".join(current_chunk_lines).strip() + "\n")

    return chunks

def merge_all_markdown_files(
    results: List[ConversionResult],
    output_dir: Optional[str] = None,
    output_filename: str = "Tong_Hop_Tai_Lieu.md"
) -> Optional[str]:
    """Gộp nội dung nhiều file kết quả thành 1 file duy nhất."""
    valid_results = [r for r in results if r.success and r.cleaned_markdown.strip()]
    if not valid_results:
        return None

    if output_dir and output_dir.strip():
        out_dir = Path(output_dir.strip())
    else:
        first_input = Path(valid_results[0].file_path)
        out_dir = first_input.parent / "md_output"

    out_dir.mkdir(parents=True, exist_ok=True)
    merged_path = out_dir / output_filename

    merged_content = []
    for r in valid_results:
        source_name = Path(r.file_path).name
        merged_content.append(f"# Nguồn: {source_name}\n\n{r.cleaned_markdown.strip()}\n\n---\n")

    final_text = "\n".join(merged_content)
    with open(merged_path, "w", encoding="utf-8") as f:
        f.write(final_text)

    log_info(f"Đã gộp {len(valid_results)} file thành: {merged_path}")
    return str(merged_path)
