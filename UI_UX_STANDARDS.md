# Chuẩn UI/UX cho ứng dụng

## Nguyên tắc chung
- Giao diện tối giản, tập trung vào nhiệm vụ chính của từng vai trò.
- Trạng thái rỗng (empty state) rõ ràng, hướng dẫn bước tiếp theo.
- Phản hồi hệ thống: dùng `flash` với phân loại success/info/warning/error.
- Thành phần giao diện đồng nhất: dùng Bootstrap 5, tránh CSS nội tuyến.
- Dùng layout chung `layouts/base.html`; mọi trang đặt nội dung trong `.container`.

## Thành phần
- Navbar: tên hệ thống, menu vai trò, Logout.
- Breadcrumb: chỉ ra ngữ cảnh trang.
- Cards cho KPI: tiêu đề nhỏ, số lớn, mô tả ngắn.
- Tables: `table-sm`, `table-striped`, căn cột cuối `text-end` cho hành động.
- Forms: label rõ ràng, mô tả placeholder, kiểm lỗi cạnh trường.

## Tính truy cập (a11y)
- Tương phản màu đạt chuẩn, có aria-label cho nút chỉ icon.
- Phím tắt cho hành động thường (sau này).

## Hiệu năng
- Truy vấn tối ưu, thống kê trước khi render.
- Phân trang cho danh sách dài (>= 20 dòng).

## Di động
- Responsive, lưới Bootstrap, nút bấm cách nhau tối thiểu 8px.


