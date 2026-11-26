import os
from pathlib import Path
import datetime
import openpyxl
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
import pymupdf
from PIL import Image, ImageDraw, ImageFont

def generate_samples(samples_dir: Path):
    samples_dir.mkdir(parents=True, exist_ok=True)
    print(f"Bắt đầu tạo các file mẫu trong: {samples_dir}")

    # 1. Excel nhiều sheet có ô gộp và công thức
    multi_excel_path = samples_dir / "sample_multi_sheet.xlsx"
    wb = openpyxl.Workbook()

    # Sheet 1: Báo cáo tài chính
    ws1 = wb.active
    ws1.title = "Báo Cáo Tài Chính"
    ws1.merge_cells("A1:D1")
    ws1["A1"] = "BÁO CÁO DOANH THU & CHI PHÍ QUÝ 1/2026"

    headers1 = ["Khoản Mục", "Tháng 1", "Tháng 2", "Tháng 3"]
    for col_idx, h in enumerate(headers1, 1):
        ws1.cell(row=2, column=col_idx, value=h)

    rows1 = [
        ["Doanh thu dịch vụ", 15000000.0, 18500000.0, 22000000.0],
        ["Doanh thu phần mềm", 25000000.0, 27000000.0, 31000000.0],
        ["Chi phí vận hành", 8000000.0, 8500000.0, 9000000.0],
        ["Chi phí nhân sự", 12000000.0, 12000000.0, 12500000.0],
        ["Tổng lợi nhuận", 20000000.0, 25000000.0, 31500000.0],  # Giá trị tính toán
    ]
    for r_idx, row_data in enumerate(rows1, 3):
        for c_idx, val in enumerate(row_data, 1):
            ws1.cell(row=r_idx, column=c_idx, value=val)

    # Sheet 2: Danh sách nhân sự
    ws2 = wb.create_sheet(title="Nhân Sự")
    headers2 = ["Mã NV", "Họ và Tên", "Phòng Ban", "Ngày Vào Làm", "Trạng Thái"]
    for col_idx, h in enumerate(headers2, 1):
        ws2.cell(row=1, column=col_idx, value=h)

    staff = [
        ["NV001", "Nguyễn Văn An", "Kỹ thuật", datetime.date(2023, 5, 10), "Đang làm việc"],
        ["NV002", "Trần Thị Bình", "Kế toán", datetime.date(2024, 1, 15), "Đang làm việc"],
        ["NV003", "Lê Hoàng Cường", "Kinh doanh", datetime.date(2025, 8, 20), "Thử việc"],
        ["NV004", "Phạm Minh Đức", "R&D", datetime.date(2022, 11, 1), "Đang làm việc"],
    ]
    for r_idx, row_data in enumerate(staff, 2):
        for c_idx, val in enumerate(row_data, 1):
            ws2.cell(row=r_idx, column=c_idx, value=val)

    # Sheet 3: Sheet phụ ẩn
    ws3 = wb.create_sheet(title="Cấu Hình Nội Bộ")
    ws3["A1"] = "Thông số hệ thống bảo mật nội bộ"
    ws3["A2"] = 123456
    ws3.sheet_state = "hidden"

    wb.save(str(multi_excel_path))
    wb.close()
    print("✅ Đã tạo sample_multi_sheet.xlsx")

    # 2. Excel lớn 5.000 dòng
    large_excel_path = samples_dir / "sample_large_5000.xlsx"
    wb_large = openpyxl.Workbook()
    ws_large = wb_large.active
    ws_large.title = "GiaoDich5000"
    ws_large.append(["Mã Giao Dịch", "Khách Hàng", "Loại Dịch Vụ", "Số Tiền", "Ngày Giao Dịch", "Trạng Thái"])

    for i in range(1, 5001):
        ws_large.append([
            f"GD{i:06d}",
            f"Khách hàng số {i}",
            "Nâng cấp gói dịch vụ AI" if i % 2 == 0 else "Gia hạn tài khoản",
            float(150000 + (i % 10) * 25000),
            datetime.date(2026, 1, 1) + datetime.timedelta(days=i % 300),
            "Thành công" if i % 15 != 0 else "Chờ xử lý"
        ])
    wb_large.save(str(large_excel_path))
    wb_large.close()
    print("✅ Đã tạo sample_large_5000.xlsx (5000 dòng)")

    # 3. Word có bảng và danh sách
    docx_path = samples_dir / "sample_document.docx"
    doc = Document()
    doc.add_heading("TÀI LIỆU HƯỚNG DẪN BÀN GIAO CÔNG VIỆC", level=1)
    p = doc.add_paragraph("Tài liệu này được biên soạn để hướng dẫn nhân viên mới tiếp nhận và vận hành các quy trình nghiệp vụ nội bộ.")

    doc.add_heading("1. Danh sách các quy trình chính", level=2)
    doc.add_paragraph("Tiếp nhận yêu cầu từ khách hàng qua hệ thống Helpdesk.", style="List Bullet")
    doc.add_paragraph("Phân loại mức độ ưu tiên theo SLA thỏa thuận.", style="List Bullet")
    doc.add_paragraph("Điều phối kỹ sư phụ trách và cập nhật trạng thái xử lý.", style="List Bullet")
    doc.add_paragraph("Nghiệm thu và gửi báo cáo định kỳ cho ban giám đốc.", style="List Bullet")

    doc.add_heading("2. Bảng phân công nhiệm vụ", level=2)
    table = doc.add_table(rows=4, cols=4)
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Hạng mục"
    hdr_cells[1].text = "Người phụ trách"
    hdr_cells[2].text = "Hạn chót"
    hdr_cells[3].text = "Ghi chú"

    data = [
        ["Hạ tầng Cloud & Server", "Nguyễn Văn An", "15/12/2026", "Đã kiểm tra backup"],
        ["Cơ sở dữ liệu PostgreSQL", "Lê Hoàng Cường", "20/12/2026", "Đã cấu hình failover"],
        ["Giao diện người dùng Web & App", "Phạm Minh Đức", "25/12/2026", "Đang thử nghiệm UAT"],
    ]
    for row_idx, row_values in enumerate(data, 1):
        row_cells = table.rows[row_idx].cells
        for col_idx, cell_value in enumerate(row_values):
            row_cells[col_idx].text = cell_value

    doc.save(str(docx_path))
    print("✅ Đã tạo sample_document.docx")

    # 4. PDF có chữ rõ ràng
    pdf_text_path = samples_dir / "sample_text.pdf"
    pdf_doc = pymupdf.open()
    page1 = pdf_doc.new_page()
    page1.insert_text(
        (50, 72),
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n\n"
        "QUY ĐỊNH BẢO MẬT THÔNG TIN VÀ AN TOÀN DỮ LIỆU\n\n"
        "Điều 1: Mọi nhân viên có trách nhiệm bảo vệ thông tin khách hàng và dữ liệu nội bộ công ty.\n"
        "Điều 2: Không được cung cấp tài khoản, mật khẩu hoặc khóa API cho bên thứ ba khi chưa được sự cho phép bằng văn bản.\n"
        "Điều 3: Các tài liệu khi đưa vào các mô hình ngôn ngữ lớn (ChatGPT, Claude) cần được chuyển đổi sang định dạng Markdown rút gọn để bảo đảm an toàn và tối ưu chi phí token.\n\n"
        "Ban Giám Đốc đã ký và phê duyệt."
    )
    pdf_doc.save(str(pdf_text_path))
    pdf_doc.close()
    print("✅ Đã tạo sample_text.pdf")

    # 5. PDF scan (mô phỏng trang scan bằng ảnh chứa chữ)
    pdf_scan_path = samples_dir / "sample_scanned.pdf"
    img = Image.new("RGB", (1200, 1600), color="white")
    draw = ImageDraw.Draw(img)
    # Vẽ các dòng mô phỏng văn bản scan
    draw.rectangle([100, 100, 1100, 1500], outline="black", width=2)
    draw.text((150, 150), "BIEN BAN KIEM KE TAI SAN DANG SCAN", fill="black")
    draw.text((150, 250), "Ngay kiem ke: 26/11/2026", fill="black")
    draw.text((150, 320), "Don vi: Phong Cong Nghe Thong Tin Lilbow", fill="black")
    draw.text((150, 400), "Trang thai: Da xac nhan day du thiet bi", fill="black")

    img_temp_path = samples_dir / "temp_scan.png"
    img.save(str(img_temp_path))

    pdf_scan_doc = pymupdf.open()
    rect = pymupdf.Rect(0, 0, 595, 842)
    scan_page = pdf_scan_doc.new_page(width=595, height=842)
    scan_page.insert_image(rect, filename=str(img_temp_path))
    pdf_scan_doc.save(str(pdf_scan_path))
    pdf_scan_doc.close()

    if img_temp_path.exists():
        img_temp_path.unlink()
    print("✅ Đã tạo sample_scanned.pdf")

    # 6. PowerPoint thuyết trình
    pptx_path = samples_dir / "sample_presentation.pptx"
    prs = Presentation()

    # Slide 1: Trang bìa
    slide1 = prs.slides.add_slide(prs.slide_layouts[0])
    slide1.shapes.title.text = "CHIẾN LƯỢC PHÁT TRIỂN SẢN PHẨM 2026"
    slide1.placeholders[1].text = "Trình bày bởi Ban Quản lý Dự án LilbowMdConvert"
    slide1.notes_slide.notes_text_frame.text = "Chào mừng quý đối tác và đại biểu tham dự buổi hội thảo chiến lược."

    # Slide 2: Mục tiêu trọng tâm
    slide2 = prs.slides.add_slide(prs.slide_layouts[1])
    slide2.shapes.title.text = "Mục tiêu trọng tâm"
    tf = slide2.placeholders[1].text_frame
    tf.text = "Tối ưu hóa token khi giao tiếp với AI Agent"
    p1 = tf.add_paragraph()
    p1.text = "Hỗ trợ định dạng phong phú: Excel, Word, PDF, PowerPoint"
    p2 = tf.add_paragraph()
    p2.text = "Bảo mật dữ liệu tuyệt đối và hoạt động hoàn toàn offline"
    slide2.notes_slide.notes_text_frame.text = "Nhấn mạnh giải pháp tiết kiệm chi phí đến 40-70% token cho doanh nghiệp."

    prs.save(str(pptx_path))
    print("✅ Đã tạo sample_presentation.pptx")

if __name__ == "__main__":
    generate_samples(Path(__file__).parent)
