# LilbowMdConvert - Phần Mềm Chuyển Đổi Tài Liệu Sang Markdown Siêu Gọn Nhẹ

Phần mềm máy tính Windows chuyên dụng để chuyển đổi các tệp **Excel, Word, PDF, PowerPoint** sang định dạng **Markdown (.md)** siêu gọn nhẹ, được làm sạch thông minh nhằm **tiết kiệm tối đa token khi đưa vào ChatGPT, Claude, Gemini hoặc các AI Agent**.

Phần mềm được thiết kế với giao diện đồ họa trực quan 100% bằng tiếng Việt, thân thiện và cực kỳ dễ dùng bằng chuột, ngay cả với người không có kiến thức về lập trình.

---

## 🌟 Các Tính Năng Nổi Bật

1. **Hỗ trợ định dạng phong phú:**
   - **Excel:** `.xlsx`, `.xls`, `.xlsm`, `.csv` (xử lý ô gộp, công thức tính toán, tự động chuyển đổi bảng lớn sang CSV để tiết kiệm token).
   - **Word:** `.docx`, `.doc` (giữ nguyên tiêu đề cấp bậc `#`, danh sách gạch đầu dòng, bảng biểu).
   - **PDF:** Trích xuất văn bản nhanh, gộp các dòng ngắt đoạn vô lý thành câu liền mạch, hỗ trợ **OCR tiếng Việt & tiếng Anh** cho tài liệu scan.
   - **PowerPoint:** `.pptx` (giữ tiêu đề, danh sách nội dung và tùy chọn giữ ghi chú của diễn giả).

2. **Bộ lọc làm sạch (Cleaner) tối ưu token chuyên sâu:**
   - Tự động xóa `NaN`, `None`, `null`, `Unnamed: n`, ô trống thừa thãi.
   - Xóa bỏ triệt để các hàng bảng và cột bảng rỗng hoàn toàn.
   - Gộp khoảng trắng thừa và hàng loạt dòng trống liên tiếp thành tối đa 1 dòng trống.
   - Rút gọn đường phân cách gạch ngang dài thành `---`.
   - Phát hiện và loại bỏ số trang, tiêu đề lặp đi lặp lại ở nhiều trang (header/footer).
   - Xóa link ảnh nhúng dạng base64 (nguyên nhân hàng đầu gây lãng phí hàng chục nghìn token).
   - Tùy chọn bỏ định dạng nhấn mạnh (**đậm**, *nghiêng*) để văn bản nhẹ hơn.

3. **3 Cấu hình mẫu (Presets) tiện lợi:**
   - ⚡ **Cân bằng (Mặc định):** Giữ nguyên độ dễ đọc, làm sạch mọi dữ liệu rác, tự động dùng CSV cho bảng trên 50 dòng.
   - 🚀 **Giảm tối đa token:** Bật toàn bộ các bộ lọc, bỏ in đậm/nghiêng, xuất bảng Excel dạng CSV.
   - 📄 **Giữ nguyên bản:** Giữ lại tối đa cấu trúc gốc của tài liệu.

4. **Quản lý Token trước & sau chuyển đổi (Kiểm soát chi phí tức thì):**
   - **Tính token ngay khi chọn/thả file:** Ngay khi bạn thêm tài liệu vào phần mềm (trước khi bấm chuyển đổi), luồng ngầm sẽ lập tức tính toán chính xác số token ban đầu của từng file và tổng cả lô. Bạn có thể bấm vào từng file để xem trước nội dung gốc và số lượng token thô của file đó.
   - **So sánh trực quan sau khi chuyển đổi:** Cập nhật ngay số token sau khi làm sạch, % token đã tiết kiệm được và chi phí ước tính (USD và VNĐ) cho các mô hình AI: **GPT-4o, GPT-4o-mini, Claude 3.5 Sonnet, Claude 3.5 Haiku, Gemini Flash**.
   - Cảnh báo màu vàng nổi bật nếu tài liệu vượt quá 100.000 token.

5. **Chia nhỏ & Gộp file thông minh:**
   - **Chia nhỏ file lớn:** Tự động cắt thành các phần nhỏ (ví dụ 30.000 token/phần) tại ranh giới tiêu đề, tuyệt đối **không cắt đứt đôi bảng biểu hay khối mã**.
   - **Gộp file:** Tùy chọn gộp toàn bộ các tài liệu trong lô thành một file Markdown duy nhất có mục lục nguồn rõ ràng.

6. **Xem trước và Sao chép 1 chạm:**
   - Xem trước nội dung Markdown ngay trên cửa sổ chính.
   - Nút **"📋 Sao chép vào clipboard"** để dán thẳng vào ChatGPT/Claude mà không cần mở file.

---

## 🖥️ Hướng Dẫn Sử Dụng Bằng Chuột

1. **Thêm tài liệu:**
   - Cách 1: Bấm nút **"➕ Thêm file"** để chọn một hoặc nhiều file.
   - Cách 2: Bấm nút **"📁 Thêm thư mục"** để quét toàn bộ file hợp lệ trong thư mục và các thư mục con.
   - Cách 3: **Kéo thả chuột** trực tiếp file hoặc thư mục từ màn hình máy tính vào bảng danh sách.
2. **Chọn cấu hình:**
   - Chọn Preset ở menu trên cùng (mặc định là *Cân bằng*).
   - Hoặc chuyển sang tab **"⚙️ Cài đặt"** để bật/tắt riêng từng quy tắc theo nhu cầu của bạn.
3. **Bắt đầu chuyển đổi:**
   - Bấm nút xanh **"🚀 Bắt đầu chuyển đổi"**. Phần mềm sẽ xử lý ngầm, thanh tiến trình hiển thị rõ ràng từng file.
   - Nếu muốn dừng, bạn có thể bấm nút **"⏹️ Hủy"** bất kỳ lúc nào.
4. **Xem kết quả & Sử dụng:**
   - Bấm chuột vào bất kỳ dòng file nào trên bảng để xem nội dung Markdown ở khung bên phải.
   - Bấm **"📋 Sao chép vào clipboard"** để copy nhanh nội dung.
   - Bấm nút **"📂 Mở thư mục kết quả"** để xem các file `.md` đã lưu (mặc định nằm trong thư mục `md_output` cạnh file gốc).

---

## 🔍 Hướng Dẫn Cài Đặt Tesseract OCR (Dành Cho PDF Scan)

Nếu tài liệu PDF của bạn là văn bản thông thường (có thể bôi đen chọn chữ), phần mềm **hoàn toàn không cần cài đặt gì thêm**.

Nếu tài liệu là **ảnh chụp scan**, để phần mềm nhận diện được chữ tiếng Việt và tiếng Anh, bạn hãy cài đặt Tesseract theo 3 bước cực kỳ đơn giản sau:

1. **Tải bộ cài đặt Tesseract cho Windows:**
   - Tải file cài đặt `.exe` mới nhất từ đường dẫn chính thức:  
     👉 [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)  
     *(Ví dụ: file `tesseract-ocr-w64-setup-5.x.x.exe`)*
2. **Chọn gói ngôn ngữ Tiếng Việt khi cài:**
   - Trong quá trình bấm `Next`, tại bước **"Choose Components"**, hãy tìm mục **"Additional language data (download)"**.
   - Tích chọn thêm vào ô: **Vietnamese** (và English nếu chưa có).
3. **Hoàn tất:**
   - Cài đặt vào đường dẫn mặc định (`C:\Program Files\Tesseract-OCR`).
   - Khởi động lại phần mềm **LilbowMdConvert**, phần mềm sẽ tự động nhận diện và kích hoạt tính năng đọc PDF scan!

---

## 📦 Hướng Dẫn Đóng Gói Thành File EXE

Dự án đã chuẩn bị sẵn file kịch bản tự động `build.bat`:

1. Mở thư mục dự án trên máy Windows.
2. Bấm đúp chuột vào file **`build.bat`**.
3. Chọn chế độ đóng gói:
   - **Lựa chọn 1 (`--onefile`):** Đóng gói thành 1 file duy nhất `LilbowMdConvert.exe` nằm trong thư mục `dist\`. Bạn có thể chép file này sang các máy tính khác chạy mà không cần cài đặt Python.
   - **Lựa chọn 2 (`--onedir`):** Đóng gói thành thư mục chứa file chạy `dist\LilbowMdConvert\LilbowMdConvert.exe`. Chế độ này khởi động cực nhanh và tránh bị phần mềm diệt virus báo nhầm.

---

## ❓ Xử Lý Các Tình Huống Lỗi Thường Gặp (FAQ)

- **Hỏi: Phần mềm báo "Hãy đóng file rồi thử lại"?**  
  *Đáp:* File Excel hoặc Word đó đang được mở bởi ứng dụng Microsoft Office trên máy bạn, khiến hệ điều hành khóa file. Bạn chỉ cần lưu và đóng cửa sổ Excel/Word đó lại rồi bấm chuyển đổi lại.

- **Hỏi: Phần mềm báo "File có mật khẩu bảo vệ, chưa hỗ trợ"?**  
  *Đáp:* File của bạn đang được cài mật khẩu mở tài liệu. Vui lòng mở file bằng Office, xóa mật khẩu bảo vệ rồi thực hiện lại.

- **Hỏi: File .doc hoặc .xls đời cũ báo cần LibreOffice?**  
  *Đáp:* Các định dạng nhị phân cổ (.doc, .xls từ Microsoft Office 2003 trở về trước) không có chuẩn mở. Hãy mở file trong Word/Excel và chọn **Save As** sang `.docx` / `.xlsx`, hoặc cài đặt phần mềm miễn phí LibreOffice trên máy để công cụ tự động chuyển đổi.

- **Hỏi: Một file bị lỗi thì cả lô có bị dừng không?**  
  *Đáp:* Không! Phần mềm xử lý độc lập từng file. File nào bị lỗi sẽ hiển thị nguyên nhân tiếng Việt cụ thể trên bảng và ghi log chi tiết vào thư mục `logs/app.log`, các file còn lại vẫn tiếp tục được chuyển đổi bình thường.

---

*Phát triển bởi Lilbow Nguyen - Tối ưu hóa cho kỷ nguyên AI Agent.*
