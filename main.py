import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from app.gui import MainWindow
from app.logger import log_error, log_info, setup_logger

def main():
    # Khởi tạo logging
    logger = setup_logger()
    log_info("=== Khởi động ứng dụng LilbowMdConvert ===")

    app = QApplication(sys.argv)
    app.setApplicationName("LilbowMdConvert")

    # Đặt icon nếu có
    icon_path = Path(__file__).parent / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        err_msg = traceback.format_exc()
        log_error(f"Lỗi nghiêm trọng không mong muốn: {err_msg}")
        QMessageBox.critical(
            None,
            "Lỗi nghiêm trọng",
            f"Đã xảy ra lỗi không mong muốn:\n{e}\n\nVui lòng kiểm tra file logs/app.log để biết chi tiết."
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
