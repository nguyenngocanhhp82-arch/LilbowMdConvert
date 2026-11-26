import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

SETTINGS_FILENAME = "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    # Thư mục xuất đầu ra ("" nghĩa là tạo thư mục "md_output" cạnh file gốc)
    "output_dir": "",
    # Cách giải quyết khi trùng tên file: "ask", "overwrite", "skip", "rename"
    "name_conflict_mode": "rename",

    # Các quy tắc làm sạch để giảm token
    "cleaner_rules": {
        "remove_nan_unnamed": True,
        "remove_empty_rows_cols": True,
        "collapse_whitespace": True,
        "shorten_dividers": True,
        "remove_repeated_headers": True,
        "remove_images": True,
        "strip_emphasis": False,
    },

    # Tùy chọn xử lý Excel
    "excel_export_mode": "auto",       # "markdown", "csv", "auto" (bảng > 50 dòng dùng CSV)
    "excel_auto_threshold": 50,        # Ngưỡng dòng để tự chuyển sang CSV
    "excel_skip_hidden_sheets": True,  # Bỏ qua sheet ẩn
    "excel_limit_rows": 0,             # 0 = không giới hạn, >0 = chỉ lấy N dòng đầu
    "excel_compact_numbers": True,     # 1.0 -> 1, bỏ số 0 thừa sau dấu phẩy
    "excel_format_dates": True,        # YYYY-MM-DD

    # Tùy chọn PDF & OCR
    "enable_ocr": True,                # Bật OCR cho trang scan
    "ocr_lang": "vie+eng",             # Gói ngôn ngữ OCR
    "ocr_dpi": 300,                    # DPI khi trích xuất ảnh scan
    "pdf_page_markers": True,          # Đánh dấu trang <!-- trang X -->

    # Tùy chọn PowerPoint & Word
    "pptx_keep_notes": True,           # Giữ ghi chú diễn giả PowerPoint

    # Tùy chọn nâng cao: Chia nhỏ hoặc Gộp file
    "split_enabled": False,            # Tự động chia nhỏ nếu file quá lớn
    "split_token_limit": 30000,        # Ngưỡng token mỗi phần
    "merge_all": False,                # Gộp tất cả file thành 1 file .md

    # Tùy chọn mô hình ước tính chi phí
    "pricing_model": "GPT-4o",

    # Preset hiện tại
    "current_preset": "Cân bằng",

    # Giao diện
    "theme": "system",                 # "system", "dark", "light"
}

PRESETS: Dict[str, Dict[str, Any]] = {
    "Giảm tối đa token": {
        "cleaner_rules": {
            "remove_nan_unnamed": True,
            "remove_empty_rows_cols": True,
            "collapse_whitespace": True,
            "shorten_dividers": True,
            "remove_repeated_headers": True,
            "remove_images": True,
            "strip_emphasis": True,
        },
        "excel_export_mode": "csv",
        "excel_skip_hidden_sheets": True,
        "excel_compact_numbers": True,
        "excel_format_dates": True,
        "pdf_page_markers": False,
        "pptx_keep_notes": False,
    },
    "Cân bằng": {
        "cleaner_rules": {
            "remove_nan_unnamed": True,
            "remove_empty_rows_cols": True,
            "collapse_whitespace": True,
            "shorten_dividers": True,
            "remove_repeated_headers": True,
            "remove_images": True,
            "strip_emphasis": False,
        },
        "excel_export_mode": "auto",
        "excel_auto_threshold": 50,
        "excel_skip_hidden_sheets": True,
        "excel_compact_numbers": True,
        "excel_format_dates": True,
        "pdf_page_markers": True,
        "pptx_keep_notes": True,
    },
    "Giữ nguyên bản": {
        "cleaner_rules": {
            "remove_nan_unnamed": False,
            "remove_empty_rows_cols": False,
            "collapse_whitespace": False,
            "shorten_dividers": False,
            "remove_repeated_headers": False,
            "remove_images": False,
            "strip_emphasis": False,
        },
        "excel_export_mode": "markdown",
        "excel_skip_hidden_sheets": False,
        "excel_compact_numbers": False,
        "excel_format_dates": False,
        "pdf_page_markers": True,
        "pptx_keep_notes": True,
    }
}

def get_settings_path() -> Path:
    """Trả về đường dẫn file settings.json đặt cạnh file exe hoặc script."""
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / SETTINGS_FILENAME

class SettingsManager:
    """Quản lý đọc/ghi cài đặt ứng dụng một cách an toàn."""
    def __init__(self):
        self._settings: Dict[str, Any] = copy.deepcopy(DEFAULT_SETTINGS)
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value

    def get_all(self) -> Dict[str, Any]:
        return copy.deepcopy(self._settings)

    def load(self) -> Dict[str, Any]:
        path = get_settings_path()
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge loaded settings into default_settings to guarantee completeness
                    for k, v in loaded.items():
                        if isinstance(v, dict) and isinstance(self._settings.get(k), dict):
                            self._settings[k].update(v)
                        else:
                            self._settings[k] = v
            except Exception as e:
                # Nếu file hỏng, giữ nguyên default
                pass
        return self.get_all()

    def save(self) -> bool:
        path = get_settings_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            return False

    def reset_to_defaults(self) -> None:
        self._settings = copy.deepcopy(DEFAULT_SETTINGS)
        self.save()

    def apply_preset(self, preset_name: str) -> None:
        if preset_name in PRESETS:
            preset_data = PRESETS[preset_name]
            for k, v in preset_data.items():
                if isinstance(v, dict) and isinstance(self._settings.get(k), dict):
                    self._settings[k].update(v)
                else:
                    self._settings[k] = v
            self._settings["current_preset"] = preset_name
            self.save()

# Instance toàn cục để tái sử dụng
settings_manager = SettingsManager()
