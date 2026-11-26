@echo off
chcp 65001 > nul
echo =====================================================================
echo       LILBOW MD CONVERT - TIẾN TRÌNH ĐÓNG GÓI RA FILE EXE WINDOWS
echo =====================================================================
echo.

REM Kiểm tra môi trường Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Máy tính chưa cài đặt Python hoặc chưa thêm Python vào biến môi trường PATH!
    echo Vui lòng cài đặt Python 3.11+ từ https://www.python.org/
    pause
    exit /b 1
)

echo [1/3] Đang cài đặt / cập nhật các thư viện phụ thuộc...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [CẢNH BÁO] Cài đặt thư viện gặp trục trặc, vẫn tiếp tục thử đóng gói...
)

echo.
echo [2/3] Chọn chế độ đóng gói:
echo   1. Đóng gói 1 file EXE duy nhất (--onefile) [Khuyên dùng, gọn nhẹ, dễ gửi]
echo   2. Đóng gói thư mục giải nén (--onedir) [Khởi động tức thì, tránh lỗi Antivirus]
set /p build_choice="Nhập lựa chọn của bạn (1 hoặc 2, mặc định 1): "

if "%build_choice%"=="2" (
    echo.
    echo Đang thực hiện đóng gói theo chế độ --onedir...
    pyinstaller --noconfirm --onedir --windowed ^
        --name LilbowMdConvert ^
        --icon icon.ico ^
        --collect-all markitdown ^
        --collect-all magika ^
        main.py
) else (
    echo.
    echo Đang thực hiện đóng gói theo chế độ --onefile...
    pyinstaller --noconfirm --onefile --windowed ^
        --name LilbowMdConvert ^
        --icon icon.ico ^
        --collect-all markitdown ^
        --collect-all magika ^
        main.py
)

if %errorlevel% neq 0 (
    echo.
    echo [LỖI] Tiến trình đóng gói PyInstaller thất bại!
    echo Hãy kiểm tra thông báo lỗi bên trên.
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Sao chép file cấu hình và tài liệu...
if exist dist\LilbowMdConvert (
    copy icon.ico dist\LilbowMdConvert\ > nul 2>&1
    copy README.md dist\LilbowMdConvert\ > nul 2>&1
) else (
    copy icon.ico dist\ > nul 2>&1
    copy README.md dist\ > nul 2>&1
)

echo.
echo =====================================================================
echo  ĐÓNG GÓI HOÀN TẤT THÀNH CÔNG!
echo  File kết quả nằm trong thư mục: dist\
echo =====================================================================
pause
