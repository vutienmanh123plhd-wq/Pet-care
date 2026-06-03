# PetCare Web - Hệ thống quản lý cửa hàng chăm sóc thú cưng

Source code demo theo file `BTL_NMCNPM_N09.docx`.

## Công nghệ

- Python chuẩn, không cần cài thêm package.
- SQLite database thật tại `data/petcare.db`.
- Giao diện HTML/CSS đơn giản.

## Cách chạy

```powershell
cd C:\Users\quang\Desktop\btl_cnpm\petcare_web
python app.py
```

Mở trình duyệt:

```text
http://127.0.0.1:8000
```

## Tài khoản mẫu

Mật khẩu của tất cả tài khoản mẫu: `123456`

| Vai trò | Email |
|---|---|
| Khách hàng | `khach@example.com` |
| Nhân viên | `nhanvien@example.com` |
| Quản lý | `quanly@example.com` |

## Chức năng chính

- Khách hàng: đăng ký, đăng nhập, xem dịch vụ, đặt lịch hẹn, xem lịch hẹn, xem chi tiết, hủy lịch.
- Nhân viên: kiểm tra lịch hẹn, tìm khách hàng, xem chi tiết lịch, tạo hóa đơn.
- Quản lý: quản lý dịch vụ, xem thống kê doanh thu, lịch hẹn, khách hàng và lượt sử dụng dịch vụ.

## CSDL

Các bảng chính:

- `users`
- `services`
- `appointments`
- `appointment_services`
- `invoices`
- `invoice_details`

Database được tự động tạo và seed dữ liệu mẫu khi chạy lần đầu.
