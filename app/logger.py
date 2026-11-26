import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, List, Optional

LOGGER_NAME = "LilbowMdConvert"
_gui_log_callbacks: List[Callable[[str, str], None]] = []

def get_log_dir() -> Path:
    """Trả về đường dẫn thư mục lưu file log (cạnh file exe hoặc file script)."""
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir

class GUILogHandler(logging.Handler):
    """Handler gửi thông điệp log trực tiếp đến giao diện người dùng."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            level = record.levelname
            for callback in _gui_log_callbacks:
                try:
                    callback(msg, level)
                except Exception:
                    pass
        except Exception:
            self.handleError(record)

def setup_logger(debug: bool = False) -> logging.Logger:
    """Khởi tạo hệ thống ghi log tập trung."""
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Console Stream Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(console_handler)

    # 2. Rotating File Handler (tối đa 5MB, giữ 3 bản sao lưu)
    try:
        log_file = get_log_dir() / "app.log"
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f"Không thể khởi tạo file log: {e}\n")

    # 3. GUI Handler
    gui_handler = GUILogHandler()
    gui_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    gui_handler.setLevel(logging.INFO)
    logger.addHandler(gui_handler)

    return logger

def add_gui_log_callback(cb: Callable[[str, str], None]) -> None:
    """Đăng ký hàm callback nhận log để hiển thị lên GUI."""
    if cb not in _gui_log_callbacks:
        _gui_log_callbacks.append(cb)

def remove_gui_log_callback(cb: Callable[[str, str], None]) -> None:
    """Hủy đăng ký hàm callback nhận log."""
    if cb in _gui_log_callbacks:
        _gui_log_callbacks.remove(cb)

def get_logger() -> logging.Logger:
    """Lấy logger chính của ứng dụng."""
    return logging.getLogger(LOGGER_NAME)

def log_info(msg: str) -> None:
    get_logger().info(msg)

def log_warning(msg: str) -> None:
    get_logger().warning(msg)

def log_error(msg: str, exc_info: bool = False) -> None:
    get_logger().error(msg, exc_info=exc_info)

def log_debug(msg: str) -> None:
    get_logger().debug(msg)
