# Yêu cầu Dashboard theo vai trò

Mục tiêu: Chuẩn hóa các Dashboard theo vai trò (Admin, HR, Interviewer, Executive) để thống nhất UI/UX, dữ liệu và hành động nhanh, phù hợp RBAC.

## URL và template
- Admin: `/dashboard/admin` → `app/templates/dashboard/admin.html`
- HR: `/dashboard/hr` → `app/templates/dashboard/hr.html`
- Interviewer: `/dashboard/interviewer` → `app/templates/dashboard/interviewer_dashboard.html`
- Executive: `/dashboard/executive` → `app/templates/dashboard/executive_dashboard.html`

Tất cả kế thừa layout chung `app/templates/layouts/base.html` và hiển thị `flash` messages.

## Quy tắc dữ liệu chung
- Sử dụng ORM theo `app/models.py` (tránh trường không tồn tại).
- Step1/2/3:
  - Step1 dựa vào `AssessmentResult.step == 'step1'`.
  - Step2 dựa vào `InterviewEvaluation.step == 'step2'` và coi “hoàn tất” nếu `recommendation != None`.
  - Step3/hiring dựa vào `ExecutiveDecision.status == 'completed'` và `final_decision == 'hire'`.

## Admin Dashboard
Khối chức năng:
- KPIs tổng quan: tổng ứng viên, đang chờ, đã tuyển, tỉ lệ pass Step1, tổng vị trí, tổng đánh giá, tổng phỏng vấn, tổng quyết định.
- Hoạt động: 5 ứng viên mới nhất, 5 vị trí mới nhất.
- Bảo mật: số tài khoản bị khóa (`locked_until > now`), số lần thất bại đăng nhập.
- Hiệu năng: chỉ báo placeholder `avg_response_time`, `db_performance`.
- Hành động nhanh: Quản lý người dùng, Cấu hình hệ thống, Audit Logs, Ngân hàng câu hỏi.

Tiêu chí nghiệm thu:
- Tất cả số liệu không ném lỗi, hiển thị 0 khi không có dữ liệu.
- Thời gian render < 300ms (local), tối thiểu truy vấn N+1.

## HR Dashboard
- Pipeline: pending, step1_completed, step2_completed, hired, rejected (đếm và % trên tổng).
- Danh sách ứng viên mới, vị trí đang tuyển, cảnh báo cần review thủ công (`manual_review_required`).
- Hành động nhanh: thêm ứng viên, xem danh sách, lên lịch phỏng vấn.

## Interviewer Dashboard
- Counters: tổng đánh giá của interviewer, số hoàn tất (`recommendation != None`), điểm TB (trên `score`).
- Bảng “Đã phân công”: các `InterviewEvaluation` của interviewer có `recommendation == None`.
- Bảng “Lịch sử đánh giá”: 10 mục gần nhất của interviewer có `recommendation != None`.

## Executive Dashboard
- Thống kê quyết định: tổng, đã hoàn tất, tỉ lệ hire.
- Phê duyệt lương: `compensation_status` (approved/pending).
- Hành động nhanh: mở danh sách cần duyệt.

## UI/UX
- Layout thống nhất, có navbar, breadcrumb, container có khoảng cách, trạng thái rỗng, và phân trang nơi cần.
- Sử dụng Bootstrap 5; không gắn CSS inline (trừ demo tối thiểu); màu sắc bám theo `app/static/css/main.css`.

## RBAC
- Truy cập dashboard theo vai trò; API endpoint dùng decorator `@hr_required` khi áp dụng.

## Theo dõi & Audit
- Mọi hành động chính gọi `@audit_action` hoặc `log_activity` với action cụ thể.


