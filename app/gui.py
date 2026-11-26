import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QSize, Qt, QThread, Signal
from PySide6.QtGui import QAction, QColor, QDragEnterEvent, QDropEvent, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.cleaner import clean_markdown
from app.converter import SUPPORTED_EXTENSIONS, ConversionResult, convert_single_file, merge_all_markdown_files
from app.logger import add_gui_log_callback, get_logger, log_error, log_info, remove_gui_log_callback
from app.settings import PRESETS, settings_manager
from app.tokens import estimate_cost, is_token_warning

class WorkerSignals(QObject):
    file_started = Signal(int, str)                # row, file_path
    file_finished = Signal(int, object)            # row, ConversionResult
    overall_progress = Signal(int, int)            # current, total
    log_message = Signal(str, str)                 # msg, level
    all_finished = Signal(list)                    # list of ConversionResult

class PrecalcSignals(QObject):
    file_calculated = Signal(str, int, str)        # file_path, tokens, raw_md
    batch_finished = Signal()

class TokenPrecalcWorker(QThread):
    """Luồng nền tính toán nhanh lượng token ban đầu của file ngay khi được thêm vào."""
    def __init__(self, file_paths: List[str], settings: Dict[str, any]):
        super().__init__()
        self.file_paths = file_paths
        self.settings = settings
        self.signals = PrecalcSignals()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        from app.converter import check_file_accessible, extract_raw_markdown
        for path_str in self.file_paths:
            if self._is_cancelled:
                break
            try:
                path_obj = Path(path_str)
                ok, _ = check_file_accessible(path_obj)
                if ok:
                    raw_md, tokens = extract_raw_markdown(
                        path_obj,
                        self.settings,
                        cancel_check=lambda: self._is_cancelled
                    )
                    self.signals.file_calculated.emit(path_str, tokens, raw_md)
            except Exception as e:
                log_debug(f"Không thể tính trước token cho {path_str}: {e}")
        self.signals.batch_finished.emit()

class ConversionWorker(QThread):
    def __init__(self, file_items: List[Dict[str, any]], settings: Dict[str, any]):
        super().__init__()
        self.file_items = file_items
        self.settings = settings
        self.signals = WorkerSignals()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        results: List[ConversionResult] = []
        total = len(self.file_items)

        for idx, item in enumerate(self.file_items):
            if self._is_cancelled:
                self.signals.log_message.emit("Người dùng đã hủy quá trình chuyển đổi.", "WARNING")
                break

            row = item["row"]
            path_str = item["path"]
            self.signals.file_started.emit(row, path_str)

            res = convert_single_file(
                path_str,
                settings=self.settings,
                cancel_check=lambda: self._is_cancelled,
                precomputed_raw_md=item.get("raw_md"),
                precomputed_tokens=item.get("tokens_before")
            )
            results.append(res)
            self.signals.file_finished.emit(row, res)
            self.signals.overall_progress.emit(idx + 1, total)

        # Xử lý gộp file nếu bật tùy chọn merge_all
        if not self._is_cancelled and self.settings.get("merge_all", False):
            merged_file = merge_all_markdown_files(
                results,
                output_dir=self.settings.get("output_dir", "")
            )
            if merged_file:
                self.signals.log_message.emit(f"Đã gộp tất cả thành file duy nhất: {merged_file}", "INFO")

        self.signals.all_finished.emit(results)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LilbowMdConvert - Chuyển đổi tài liệu sang Markdown gọn nhẹ")
        self.resize(1180, 750)
        self.setMinimumSize(850, 550)
        self.setAcceptDrops(True)

        self.files_data: List[Dict[str, any]] = []
        self.worker: Optional[ConversionWorker] = None
        self.precalc_workers: List[TokenPrecalcWorker] = []
        self.last_results: Dict[str, ConversionResult] = {}
        self.last_output_dir: str = ""

        # Thiết lập giao diện
        self._init_ui()
        self._setup_logging()
        self._load_settings_to_ui()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Thanh công cụ trên cùng (Thêm file, Thêm thư mục, Xóa, Cài đặt nhanh)
        top_bar = QHBoxLayout()

        self.btn_add_files = QPushButton("➕ Thêm file")
        self.btn_add_files.setFixedHeight(34)
        self.btn_add_files.clicked.connect(self._on_add_files)

        self.btn_add_folder = QPushButton("📁 Thêm thư mục")
        self.btn_add_folder.setFixedHeight(34)
        self.btn_add_folder.clicked.connect(self._on_add_folder)

        self.btn_remove_selected = QPushButton("❌ Xóa đã chọn")
        self.btn_remove_selected.setFixedHeight(34)
        self.btn_remove_selected.clicked.connect(self._on_remove_selected)

        self.btn_clear_all = QPushButton("🗑️ Xóa tất cả")
        self.btn_clear_all.setFixedHeight(34)
        self.btn_clear_all.clicked.connect(self._on_clear_all)

        top_bar.addWidget(self.btn_add_files)
        top_bar.addWidget(self.btn_add_folder)
        top_bar.addWidget(self.btn_remove_selected)
        top_bar.addWidget(self.btn_clear_all)
        top_bar.addSpacing(15)

        # Dropdown Preset
        top_bar.addWidget(QLabel("Cấu hình:"))
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(["Cân bằng", "Giảm tối đa token", "Giữ nguyên bản"])
        self.combo_preset.currentTextChanged.connect(self._on_preset_changed)
        top_bar.addWidget(self.combo_preset)

        # Dropdown Model giá
        top_bar.addWidget(QLabel("Mô hình:"))
        self.combo_model = QComboBox()
        self.combo_model.addItems(["GPT-4o", "GPT-4o-mini", "Claude 3.5 Sonnet", "Claude 3.5 Haiku", "Gemini 1.5 Flash"])
        self.combo_model.currentTextChanged.connect(self._on_model_changed)
        top_bar.addWidget(self.combo_model)

        top_bar.addStretch()

        # Nút chuyển đổi và Hủy
        self.btn_convert = QPushButton("🚀 Bắt đầu chuyển đổi")
        self.btn_convert.setFixedHeight(36)
        self.btn_convert.setStyleSheet("font-weight: bold; background-color: #2563eb; color: white; padding: 0 16px; border-radius: 4px;")
        self.btn_convert.clicked.connect(self._on_start_convert)

        self.btn_cancel = QPushButton("⏹️ Hủy")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel_convert)

        top_bar.addWidget(self.btn_convert)
        top_bar.addWidget(self.btn_cancel)
        main_layout.addLayout(top_bar)

        # 2. Thanh chọn thư mục xuất
        output_bar = QHBoxLayout()
        output_bar.addWidget(QLabel("Thư mục xuất:"))
        self.lbl_output_dir = QLabel("Mặc định: thư mục 'md_output' cạnh file gốc")
        self.lbl_output_dir.setStyleSheet("color: #4b5563; font-style: italic;")
        output_bar.addWidget(self.lbl_output_dir, stretch=1)

        self.btn_choose_output = QPushButton("Duyệt...")
        self.btn_choose_output.clicked.connect(self._on_choose_output_dir)
        self.btn_reset_output = QPushButton("Mặc định")
        self.btn_reset_output.clicked.connect(self._on_reset_output_dir)
        self.btn_open_output = QPushButton("📂 Mở thư mục kết quả")
        self.btn_open_output.clicked.connect(self._on_open_output_dir)

        output_bar.addWidget(self.btn_choose_output)
        output_bar.addWidget(self.btn_reset_output)
        output_bar.addWidget(self.btn_open_output)
        main_layout.addLayout(output_bar)

        # 3. Phân chia Splitter: Bảng file (bên trái) và Preview/Nhật ký (bên phải)
        splitter = QSplitter(Qt.Horizontal)

        # === Bên trái: Bảng danh sách file ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Tên file", "Loại", "Dung lượng", "Trạng thái", "Token trước", "Token sau", "% Giảm"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in [1, 2, 3, 4, 5, 6]:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        left_layout.addWidget(self.table)

        splitter.addWidget(left_widget)

        # === Bên phải: Tab Widget (Xem trước Markdown & Nhật ký hệ thống & Cài đặt) ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()

        # Tab 1: Xem trước Markdown
        tab_preview = QWidget()
        preview_layout = QVBoxLayout(tab_preview)
        preview_layout.setContentsMargins(4, 4, 4, 4)

        preview_top = QHBoxLayout()
        self.lbl_preview_title = QLabel("Nội dung xem trước:")
        self.lbl_preview_title.setStyleSheet("font-weight: bold;")
        preview_top.addWidget(self.lbl_preview_title, stretch=1)

        self.btn_copy_clipboard = QPushButton("📋 Sao chép vào clipboard")
        self.btn_copy_clipboard.clicked.connect(self._on_copy_clipboard)
        preview_top.addWidget(self.btn_copy_clipboard)

        preview_layout.addLayout(preview_top)

        self.txt_preview = QPlainTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setFont(QFont("Monospace", 10))
        preview_layout.addWidget(self.txt_preview)

        self.tab_widget.addTab(tab_preview, "📄 Xem trước Markdown")

        # Tab 2: Nhật ký Log
        tab_log = QWidget()
        log_layout = QVBoxLayout(tab_log)
        log_layout.setContentsMargins(4, 4, 4, 4)

        self.txt_logs = QPlainTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setFont(QFont("Monospace", 9))
        log_layout.addWidget(self.txt_logs)

        self.tab_widget.addTab(tab_log, "📝 Nhật ký hoạt động")

        # Tab 3: Cài đặt chi tiết
        tab_settings = QWidget()
        settings_outer_layout = QVBoxLayout(tab_settings)
        settings_outer_layout.setContentsMargins(4, 4, 4, 4)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        settings_layout = QVBoxLayout(scroll_content)
        settings_layout.setSpacing(10)

        # 1. Nhóm làm sạch Token
        group_cleaner = QGroupBox("Quy tắc làm sạch tiết kiệm Token (Cleaner)")
        cleaner_layout = QVBoxLayout(group_cleaner)
        self.cb_clean_nan = QCheckBox("Xóa 'NaN', 'None', 'Unnamed: n', ô trống")
        self.cb_clean_empty = QCheckBox("Xóa hàng bảng và cột bảng rỗng hoàn toàn")
        self.cb_clean_spaces = QCheckBox("Gộp khoảng trắng thừa và các dòng trống liên tiếp")
        self.cb_clean_dividers = QCheckBox("Rút gọn dòng gạch phân cách dài (---, ===)")
        self.cb_clean_form = QCheckBox("Rút gọn chuỗi chấm dài (....) và gạch dưới (____) điền form")
        self.cb_clean_headers = QCheckBox("Xóa số trang / tiêu đề lặp lại (>= 2 lần)")
        self.cb_clean_images = QCheckBox("Xóa ảnh nhúng base64 và link ảnh")
        self.cb_strip_emphasis = QCheckBox("Bỏ định dạng nhấn mạnh (**đậm**, *nghiêng*)")

        for cb in [
            self.cb_clean_nan, self.cb_clean_empty, self.cb_clean_spaces,
            self.cb_clean_dividers, self.cb_clean_form, self.cb_clean_headers,
            self.cb_clean_images, self.cb_strip_emphasis
        ]:
            cleaner_layout.addWidget(cb)
        settings_layout.addWidget(group_cleaner)

        # 2. Nhóm tùy chọn Excel
        group_excel = QGroupBox("Tùy chọn xử lý Excel (.xlsx, .csv)")
        excel_layout = QVBoxLayout(group_excel)

        h_ex_mode = QHBoxLayout()
        h_ex_mode.addWidget(QLabel("Kiểu xuất bảng:"))
        self.combo_excel_mode = QComboBox()
        self.combo_excel_mode.addItems(["Tự động (bảng > 15 dòng dùng CSV)", "Bảng Markdown (dễ đọc)", "CSV trong khối code (rẻ token)"])
        h_ex_mode.addWidget(self.combo_excel_mode, stretch=1)
        excel_layout.addLayout(h_ex_mode)

        self.cb_excel_skip_hidden = QCheckBox("Bỏ qua các sheet ẩn")
        self.cb_excel_compact_numbers = QCheckBox("Rút gọn số (1.0 thành 1, bỏ số 0 thừa)")
        self.cb_excel_format_dates = QCheckBox("Định dạng ngày tháng chuẩn gọn (YYYY-MM-DD)")
        excel_layout.addWidget(self.cb_excel_skip_hidden)
        excel_layout.addWidget(self.cb_excel_compact_numbers)
        excel_layout.addWidget(self.cb_excel_format_dates)

        h_ex_limit = QHBoxLayout()
        h_ex_limit.addWidget(QLabel("Chỉ lấy N dòng đầu mỗi sheet (0 = lấy tất cả):"))
        self.spin_excel_limit = QSpinBox()
        self.spin_excel_limit.setRange(0, 100000)
        self.spin_excel_limit.setValue(0)
        h_ex_limit.addWidget(self.spin_excel_limit)
        excel_layout.addLayout(h_ex_limit)

        settings_layout.addWidget(group_excel)

        # 3. Nhóm PDF & OCR
        group_pdf = QGroupBox("Tùy chọn PDF & OCR")
        pdf_layout = QVBoxLayout(group_pdf)
        self.cb_enable_ocr = QCheckBox("Bật OCR cho trang PDF scan (< 20 ký tự text)")
        self.cb_pdf_markers = QCheckBox("Đánh dấu số trang <!-- trang X -->")
        pdf_layout.addWidget(self.cb_enable_ocr)
        pdf_layout.addWidget(self.cb_pdf_markers)
        settings_layout.addWidget(group_pdf)

        # 4. Nhóm Chia nhỏ & Gộp file
        group_split_merge = QGroupBox("Chia nhỏ & Gộp file")
        sm_layout = QVBoxLayout(group_split_merge)
        h_split = QHBoxLayout()
        self.cb_split_files = QCheckBox("Tự động chia nhỏ nếu file quá lớn:")
        self.spin_split_tokens = QSpinBox()
        self.spin_split_tokens.setRange(5000, 200000)
        self.spin_split_tokens.setSingleStep(5000)
        self.spin_split_tokens.setValue(30000)
        h_split.addWidget(self.cb_split_files)
        h_split.addWidget(self.spin_split_tokens)
        h_split.addWidget(QLabel("tokens/phần"))
        sm_layout.addLayout(h_split)

        self.cb_merge_all = QCheckBox("Gộp tất cả file kết quả thành 1 file .md duy nhất")
        sm_layout.addWidget(self.cb_merge_all)
        settings_layout.addWidget(group_split_merge)

        # Nút Lưu và Khôi phục
        btn_box = QHBoxLayout()
        self.btn_save_settings = QPushButton("💾 Lưu cài đặt")
        self.btn_save_settings.clicked.connect(self._on_save_settings_clicked)
        self.btn_reset_settings = QPushButton("🔄 Khôi phục mặc định")
        self.btn_reset_settings.clicked.connect(self._on_reset_settings_clicked)
        btn_box.addWidget(self.btn_save_settings)
        btn_box.addWidget(self.btn_reset_settings)
        settings_layout.addLayout(btn_box)

        scroll_area.setWidget(scroll_content)
        settings_outer_layout.addWidget(scroll_area)
        self.tab_widget.addTab(tab_settings, "⚙️ Cài đặt")

        right_layout.addWidget(self.tab_widget)
        splitter.addWidget(right_widget)

        splitter.setSizes([650, 480])
        main_layout.addWidget(splitter, stretch=1)

        # 4. Thanh tiến trình và thông báo trạng thái
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar, stretch=1)

        self.lbl_status = QLabel("Sẵn sàng")
        progress_layout.addWidget(self.lbl_status)
        main_layout.addLayout(progress_layout)

        # 5. Thanh tổng kết token và chi phí
        self.lbl_summary = QLabel("Tổng token: Chưa chuyển đổi | Tiết kiệm: 0% | Chi phí ước tính: $0.00 (0 đ)")
        self.lbl_summary.setStyleSheet("font-weight: bold; padding: 6px; background-color: #f3f4f6; border-radius: 4px; color: #1f2937;")
        main_layout.addWidget(self.lbl_summary)

    def _setup_logging(self):
        def log_listener(msg: str, level: str):
            prefix = ""
            if level == "ERROR":
                prefix = "❌ "
            elif level == "WARNING":
                prefix = "⚠️ "
            elif level == "INFO":
                prefix = "ℹ️ "
            self.txt_logs.appendPlainText(f"{prefix}{msg}")
        add_gui_log_callback(log_listener)

    def _load_settings_to_ui(self):
        st = settings_manager.get_all()
        preset = st.get("current_preset", "Cân bằng")
        idx = self.combo_preset.findText(preset)
        if idx >= 0:
            self.combo_preset.blockSignals(True)
            self.combo_preset.setCurrentIndex(idx)
            self.combo_preset.blockSignals(False)

        model = st.get("pricing_model", "GPT-4o")
        m_idx = self.combo_model.findText(model)
        if m_idx >= 0:
            self.combo_model.setCurrentIndex(m_idx)

        out_dir = st.get("output_dir", "")
        if out_dir:
            self.lbl_output_dir.setText(out_dir)
            self.lbl_output_dir.setStyleSheet("color: #1f2937; font-weight: normal;")
            self.last_output_dir = out_dir

        # Cập nhật các checkbox làm sạch
        cr = st.get("cleaner_rules", {})
        self.cb_clean_nan.setChecked(cr.get("remove_nan_unnamed", True))
        self.cb_clean_empty.setChecked(cr.get("remove_empty_rows_cols", True))
        self.cb_clean_spaces.setChecked(cr.get("collapse_whitespace", True))
        self.cb_clean_dividers.setChecked(cr.get("shorten_dividers", True))
        self.cb_clean_form.setChecked(cr.get("collapse_form_lines", True))
        self.cb_clean_headers.setChecked(cr.get("remove_repeated_headers", True))
        self.cb_clean_images.setChecked(cr.get("remove_images", True))
        self.cb_strip_emphasis.setChecked(cr.get("strip_emphasis", False))

        # Cập nhật tùy chọn Excel
        ex_mode = st.get("excel_export_mode", "auto")
        if ex_mode == "auto":
            self.combo_excel_mode.setCurrentIndex(0)
        elif ex_mode == "markdown":
            self.combo_excel_mode.setCurrentIndex(1)
        elif ex_mode == "csv":
            self.combo_excel_mode.setCurrentIndex(2)

        self.cb_excel_skip_hidden.setChecked(st.get("excel_skip_hidden_sheets", True))
        self.cb_excel_compact_numbers.setChecked(st.get("excel_compact_numbers", True))
        self.cb_excel_format_dates.setChecked(st.get("excel_format_dates", True))
        self.spin_excel_limit.setValue(st.get("excel_limit_rows", 0))

        # Cập nhật PDF
        self.cb_enable_ocr.setChecked(st.get("enable_ocr", True))
        self.cb_pdf_markers.setChecked(st.get("pdf_page_markers", True))

        # Cập nhật Chia & Gộp
        self.cb_split_files.setChecked(st.get("split_enabled", False))
        self.spin_split_tokens.setValue(st.get("split_token_limit", 30000))
        self.cb_merge_all.setChecked(st.get("merge_all", False))

    def _on_preset_changed(self, preset_name: str):
        settings_manager.apply_preset(preset_name)
        self._load_settings_to_ui()
        log_info(f"Đã áp dụng cấu hình preset: '{preset_name}'")

    def _on_save_settings_clicked(self):
        st = settings_manager.get_all()
        cr = {
            "remove_nan_unnamed": self.cb_clean_nan.isChecked(),
            "remove_empty_rows_cols": self.cb_clean_empty.isChecked(),
            "collapse_whitespace": self.cb_clean_spaces.isChecked(),
            "shorten_dividers": self.cb_clean_dividers.isChecked(),
            "collapse_form_lines": self.cb_clean_form.isChecked(),
            "remove_repeated_headers": self.cb_clean_headers.isChecked(),
            "remove_images": self.cb_clean_images.isChecked(),
            "strip_emphasis": self.cb_strip_emphasis.isChecked(),
        }
        st["cleaner_rules"] = cr

        ex_idx = self.combo_excel_mode.currentIndex()
        if ex_idx == 0:
            st["excel_export_mode"] = "auto"
        elif ex_idx == 1:
            st["excel_export_mode"] = "markdown"
        else:
            st["excel_export_mode"] = "csv"

        st["excel_skip_hidden_sheets"] = self.cb_excel_skip_hidden.isChecked()
        st["excel_compact_numbers"] = self.cb_excel_compact_numbers.isChecked()
        st["excel_format_dates"] = self.cb_excel_format_dates.isChecked()
        st["excel_limit_rows"] = self.spin_excel_limit.value()

        st["enable_ocr"] = self.cb_enable_ocr.isChecked()
        st["pdf_page_markers"] = self.cb_pdf_markers.isChecked()

        st["split_enabled"] = self.cb_split_files.isChecked()
        st["split_token_limit"] = self.spin_split_tokens.value()
        st["merge_all"] = self.cb_merge_all.isChecked()

        for k, v in st.items():
            settings_manager.set(k, v)
        settings_manager.save()
        QMessageBox.information(self, "Thông báo", "Đã lưu cài đặt thành công vào settings.json!")
        log_info("Đã lưu các tùy chọn cài đặt vào file settings.json.")

    def _on_reset_settings_clicked(self):
        reply = QMessageBox.question(
            self,
            "Xác nhận",
            "Bạn có chắc chắn muốn khôi phục toàn bộ cài đặt về mặc định?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            settings_manager.reset_to_defaults()
            self._load_settings_to_ui()
            log_info("Đã khôi phục cài đặt về mặc định.")

    def _on_model_changed(self, model_name: str):
        settings_manager.set("pricing_model", model_name)
        settings_manager.save()
        self._update_summary_display()

    def _on_choose_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Chọn thư mục xuất Markdown")
        if dir_path:
            self.lbl_output_dir.setText(dir_path)
            self.lbl_output_dir.setStyleSheet("color: #1f2937; font-weight: normal;")
            self.last_output_dir = dir_path
            settings_manager.set("output_dir", dir_path)
            settings_manager.save()

    def _on_reset_output_dir(self):
        self.lbl_output_dir.setText("Mặc định: thư mục 'md_output' cạnh file gốc")
        self.lbl_output_dir.setStyleSheet("color: #4b5563; font-style: italic;")
        self.last_output_dir = ""
        settings_manager.set("output_dir", "")
        settings_manager.save()

    def _on_open_output_dir(self):
        target_dir = self.last_output_dir
        if not target_dir or not Path(target_dir).exists():
            # Thử mở thư mục kết quả của file đầu tiên
            if self.files_data:
                first_file = Path(self.files_data[0]["path"])
                target_dir = str(first_file.parent / "md_output")

        if target_dir and Path(target_dir).exists():
            if sys.platform == "win32":
                os.startfile(target_dir)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", target_dir])
            else:
                import subprocess
                subprocess.run(["xdg-open", target_dir])
        else:
            QMessageBox.information(self, "Thông báo", "Chưa có thư mục kết quả hoặc thư mục chưa được tạo.")

    def _on_add_files(self):
        filter_str = (
            "Tất cả tài liệu hỗ trợ (*.xlsx *.xls *.xlsm *.csv *.docx *.doc *.pdf *.pptx);;"
            "Bảng tính Excel (*.xlsx *.xls *.xlsm *.csv);;"
            "Văn bản Word (*.docx *.doc);;"
            "Tài liệu PDF (*.pdf);;"
            "Thuyết trình PowerPoint (*.pptx);;"
            "Mọi file (*.*)"
        )
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Chọn file cần chuyển đổi", "", filter_str)
        if file_paths:
            self._add_files_to_list(file_paths)

    def _on_add_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Chọn thư mục quét đệ quy các file tài liệu")
        if dir_path:
            matched_files = []
            for root, _, files in os.walk(dir_path):
                for f in files:
                    ext = Path(f).suffix.lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        matched_files.append(os.path.join(root, f))
            if matched_files:
                self._add_files_to_list(matched_files)
                log_info(f"Đã quét và thêm {len(matched_files)} file từ thư mục: {dir_path}")
            else:
                QMessageBox.information(self, "Thông báo", "Không tìm thấy file nào thuộc định dạng được hỗ trợ trong thư mục này.")

    def _add_files_to_list(self, paths: List[str]):
        existing_paths = {item["path"] for item in self.files_data}
        added_count = 0
        new_paths_to_precalc: List[str] = []

        for p in paths:
            path_obj = Path(p).resolve()
            if not path_obj.is_file():
                continue
            ext = path_obj.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            if str(path_obj) in existing_paths:
                continue

            try:
                size_bytes = path_obj.stat().st_size
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            except Exception:
                size_str = "N/A"

            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            item_name = QTableWidgetItem(path_obj.name)
            item_name.setToolTip(str(path_obj))
            item_ext = QTableWidgetItem(ext.upper().replace(".", ""))
            item_size = QTableWidgetItem(size_str)
            item_status = QTableWidgetItem("Chờ chuyển đổi")
            item_tb = QTableWidgetItem("⏳ Đang tính...")
            item_tb.setTextAlignment(Qt.AlignCenter)
            item_ta = QTableWidgetItem("-")
            item_red = QTableWidgetItem("-")

            for col, item in enumerate([item_name, item_ext, item_size, item_status, item_tb, item_ta, item_red]):
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_idx, col, item)

            self.files_data.append({
                "row": row_idx,
                "path": str(path_obj),
                "name": path_obj.name,
                "size_str": size_str,
                "status": "Chờ chuyển đổi",
                "tokens_before": None,
                "raw_md": None
            })
            existing_paths.add(str(path_obj))
            new_paths_to_precalc.append(str(path_obj))
            added_count += 1

        if added_count > 0:
            self.lbl_status.setText(f"Đã thêm {added_count} file mới. Đang tính trước token ban đầu...")
            self._update_summary_display()

            # Bật luồng tính trước token ban đầu cho các file vừa thêm
            precalc = TokenPrecalcWorker(new_paths_to_precalc, settings_manager.get_all())
            precalc.signals.file_calculated.connect(self._on_file_tokens_precalculated)
            precalc.signals.batch_finished.connect(self._on_precalc_batch_finished)
            precalc.start()
            self.precalc_workers.append(precalc)

    def _on_file_tokens_precalculated(self, path_str: str, tokens: int, raw_md: str):
        """Xử lý cập nhật giao diện khi một file tính xong số token ban đầu."""
        target_row = -1
        for item in self.files_data:
            if item["path"] == path_str:
                item["tokens_before"] = tokens
                item["raw_md"] = raw_md
                target_row = item["row"]
                break

        if target_row >= 0 and target_row < self.table.rowCount():
            tb_item = self.table.item(target_row, 4)
            if tb_item:
                tb_item.setText(f"{tokens:,}")
                tb_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tb_item.setToolTip(f"Số token ban đầu trước khi chuyển đổi: {tokens:,}")

        self._update_summary_display()

        # Nếu file này đang được chọn và chưa convert, cập nhật preview ngay
        selected_indexes = self.table.selectedIndexes()
        if selected_indexes:
            current_row = selected_indexes[0].row()
            if 0 <= current_row < len(self.files_data):
                if self.files_data[current_row]["path"] == path_str and path_str not in self.last_results:
                    name = Path(path_str).name
                    self.lbl_preview_title.setText(f"Xem trước (Gốc): {name} ({tokens:,} tokens - Chưa chuyển đổi)")
                    self.txt_preview.setPlainText(raw_md)

    def _on_precalc_batch_finished(self):
        """Xử lý khi hoàn thành tính trước một đợt file."""
        self._update_summary_display()

    def _on_remove_selected(self):
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()), reverse=True)
        if not selected_rows:
            return

        for r in selected_rows:
            if r < len(self.files_data):
                removed_path = self.files_data[r]["path"]
                if removed_path in self.last_results:
                    del self.last_results[removed_path]
            self.table.removeRow(r)
            del self.files_data[r]

        # Cập nhật lại row index trong files_data
        for idx, item in enumerate(self.files_data):
            item["row"] = idx

        self.lbl_status.setText(f"Đã xóa các file đã chọn. Còn lại: {len(self.files_data)} file.")
        self._update_summary_display()

    def _on_clear_all(self):
        if not self.files_data:
            return

        # Dừng các luồng tính token trước nếu còn đang chạy
        for w in self.precalc_workers:
            if w.isRunning():
                w.cancel()
        self.precalc_workers.clear()

        self.table.setRowCount(0)
        self.files_data.clear()
        self.last_results.clear()
        self.txt_preview.clear()
        self.lbl_preview_title.setText("Nội dung xem trước:")
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Đã dọn sạch danh sách file.")
        self._update_summary_display()

    # Kéo thả file / thư mục vào cửa sổ
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        file_paths = []
        for u in urls:
            local_path = u.toLocalFile()
            if os.path.isdir(local_path):
                for root, _, files in os.walk(local_path):
                    for f in files:
                        ext = Path(f).suffix.lower()
                        if ext in SUPPORTED_EXTENSIONS:
                            file_paths.append(os.path.join(root, f))
            elif os.path.isfile(local_path):
                file_paths.append(local_path)

        if file_paths:
            self._add_files_to_list(file_paths)
            event.acceptProposedAction()

    def _on_start_convert(self):
        if not self.files_data:
            QMessageBox.information(self, "Thông báo", "Vui lòng thêm ít nhất một file để chuyển đổi.")
            return

        self.btn_convert.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_add_files.setEnabled(False)
        self.btn_add_folder.setEnabled(False)
        self.btn_remove_selected.setEnabled(False)
        self.btn_clear_all.setEnabled(False)

        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.files_data))
        self.lbl_status.setText("Đang chuyển đổi...")

        st = settings_manager.get_all()
        # Chạy trong luồng nền QThread
        self.worker = ConversionWorker(self.files_data, st)
        self.worker.signals.file_started.connect(self._on_worker_file_started)
        self.worker.signals.file_finished.connect(self._on_worker_file_finished)
        self.worker.signals.overall_progress.connect(self._on_worker_progress)
        self.worker.signals.log_message.connect(lambda msg, lvl: log_info(msg))
        self.worker.signals.all_finished.connect(self._on_worker_all_finished)
        self.worker.start()

    def _on_cancel_convert(self):
        if self.worker and self.worker.isRunning():
            self.lbl_status.setText("Đang dừng tiến trình...")
            self.btn_cancel.setEnabled(False)
            self.worker.cancel()

    def _on_worker_file_started(self, row: int, path_str: str):
        if row < self.table.rowCount():
            self.table.item(row, 3).setText("⏳ Đang xử lý...")
            self.lbl_status.setText(f"Đang xử lý: {Path(path_str).name}")

    def _on_worker_file_finished(self, row: int, res: ConversionResult):
        self.last_results[res.file_path] = res
        if row < self.table.rowCount():
            if res.success:
                self.table.item(row, 3).setText("✅ Xong")
                self.table.item(row, 4).setText(f"{res.tokens_before:,}")
                self.table.item(row, 5).setText(f"{res.tokens_after:,}")
                self.table.item(row, 6).setText(f"-{res.reduction_pct:.1f}%")

                if is_token_warning(res.tokens_after):
                    self.table.item(row, 5).setToolTip("⚠️ Cảnh báo: File vượt quá 100,000 token!")
            else:
                self.table.item(row, 3).setText(f"❌ {res.error_message}")
                self.table.item(row, 3).setToolTip(res.error_message)

        # Nếu file đang được chọn trên bảng, cập nhật preview ngay
        current_row = self.table.currentRow()
        if current_row == row:
            self._display_preview(res)

    def _on_worker_progress(self, current: int, total: int):
        self.progress_bar.setValue(current)
        self.lbl_status.setText(f"Đang chuyển đổi: {current}/{total} file...")

    def _on_worker_all_finished(self, results: List[ConversionResult]):
        self.btn_convert.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_add_files.setEnabled(True)
        self.btn_add_folder.setEnabled(True)
        self.btn_remove_selected.setEnabled(True)
        self.btn_clear_all.setEnabled(True)

        success_cnt = sum(1 for r in results if r.success)
        fail_cnt = len(results) - success_cnt

        if fail_cnt == 0:
            self.lbl_status.setText(f"Hoàn tất xuất sắc! Đã chuyển đổi thành công {success_cnt}/{len(results)} file.")
        else:
            self.lbl_status.setText(f"Đã xử lý xong: {success_cnt} thành công, {fail_cnt} lỗi. Xem chi tiết trên bảng.")

        self._update_summary_display()

        # Tự động chọn dòng đầu tiên để hiển thị preview
        if self.table.rowCount() > 0 and self.table.currentRow() < 0:
            self.table.selectRow(0)

    def _on_table_selection_changed(self):
        selected_indexes = self.table.selectedIndexes()
        if not selected_indexes:
            return
        row = selected_indexes[0].row()
        if 0 <= row < len(self.files_data):
            file_info = self.files_data[row]
            path_str = file_info["path"]
            res = self.last_results.get(path_str)
            if res:
                self._display_preview(res)
            else:
                name = Path(path_str).name
                tokens = file_info.get("tokens_before")
                raw_md = file_info.get("raw_md")
                if raw_md:
                    self.lbl_preview_title.setText(f"Xem trước (Gốc): {name} ({tokens:,} tokens - Chưa chuyển đổi)")
                    self.txt_preview.setPlainText(raw_md)
                elif tokens is not None:
                    self.lbl_preview_title.setText(f"Xem trước: {name} ({tokens:,} tokens - Chưa chuyển đổi)")
                    self.txt_preview.setPlainText(
                        f"Tên file: {name}\n"
                        f"Lượng token ban đầu: {tokens:,} tokens.\n\n"
                        f"Bấm 'Bắt đầu chuyển đổi' để tiến hành làm sạch và rút gọn token."
                    )
                else:
                    self.lbl_preview_title.setText(f"Xem trước: {name} (Đang tính token...)")
                    self.txt_preview.setPlainText("Đang phân tích cấu trúc và tính toán lượng token ban đầu của file...")

    def _display_preview(self, res: ConversionResult):
        name = Path(res.file_path).name
        if res.success:
            self.lbl_preview_title.setText(f"Xem trước: {name} (Token: {res.tokens_after:,} | Giảm: -{res.reduction_pct:.1f}%)")
            self.txt_preview.setPlainText(res.cleaned_markdown)
        else:
            self.lbl_preview_title.setText(f"Lỗi: {name}")
            self.txt_preview.setPlainText(f"Không thể chuyển đổi file này.\nNguyên nhân: {res.error_message}")

    def _on_copy_clipboard(self):
        text = self.txt_preview.toPlainText()
        if not text:
            QMessageBox.information(self, "Thông báo", "Không có nội dung để sao chép.")
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.lbl_status.setText("Đã sao chép nội dung vào Clipboard! Sẵn sàng dán vào ChatGPT / Claude.")

    def _update_summary_display(self):
        model = self.combo_model.currentText()
        converted_items = [r for r in self.last_results.values() if r.success]

        if converted_items:
            # Khi đã có kết quả chuyển đổi xong
            total_before = sum(r.tokens_before for r in converted_items)
            total_after = sum(r.tokens_after for r in converted_items)
            reduction = 0.0
            if total_before > 0:
                reduction = ((total_before - total_after) / total_before) * 100.0

            usd, vnd = estimate_cost(total_after, model=model)
            warning_tag = ""
            if total_after > 100_000:
                warning_tag = " | ⚠️ Cảnh báo: Tổng token > 100k!"

            self.lbl_summary.setText(
                f"Tổng token: Trước {total_before:,} ➔ Sau {total_after:,} | Giảm: {reduction:.1f}% | "
                f"Ước tính ({model}): ~${usd:.4f} ({vnd:,.0f} đ){warning_tag}"
            )
        else:
            # Khi chưa chuyển đổi: thống kê lượng token ban đầu
            if not self.files_data:
                self.lbl_summary.setText("Chưa có file nào | Hãy chọn hoặc kéo thả file vào bảng")
                return

            known_tokens = [item["tokens_before"] for item in self.files_data if item.get("tokens_before") is not None]
            total_initial = sum(known_tokens)
            calculating_count = len(self.files_data) - len(known_tokens)

            usd, vnd = estimate_cost(total_initial, model=model)
            warning_tag = " | ⚠️ Cảnh báo: Tổng token > 100k!" if total_initial > 100_000 else ""

            if calculating_count > 0:
                self.lbl_summary.setText(
                    f"Tổng token ban đầu: {total_initial:,} tokens (đang tính {calculating_count} file...) | "
                    f"Ước tính ({model}): ~${usd:.4f} ({vnd:,.0f} đ)"
                )
            else:
                self.lbl_summary.setText(
                    f"Tổng token ban đầu: {total_initial:,} tokens | "
                    f"Ước tính ({model}): ~${usd:.4f} ({vnd:,.0f} đ){warning_tag} | Sẵn sàng chuyển đổi"
                )
