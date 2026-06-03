# PetCare Web - Module quản lý lịch hẹn

Project demo theo đề tài **Hệ thống quản lý cửa hàng chăm sóc thú cưng** trong `BTL_NMCNPM_N09.docx`.

Phần cần demo chính của nhóm/module này là **quản lý lịch hẹn**:

- Khách hàng đặt lịch hẹn.
- Khách hàng xem lịch hẹn, xem chi tiết, hủy lịch.
- Nhân viên kiểm tra lịch hẹn khách hàng, tìm kiếm và xem chi tiết.

## Bản dùng để bảo vệ: SQL Server

### 1. Cài thư viện

```powershell
cd C:\Users\quang\Desktop\btl_cnpm\petcare_web
pip install -r requirements_mssql.txt
```

### 2. Tạo database

Trong SQL Server Management Studio tạo database:

```sql
CREATE DATABASE petcare;
```

### 3. Cấu hình kết nối

Sửa file `config.py` cho đúng SQL Server của máy:

```python
DB_CONFIG = {
    "server": "localhost",
    "database": "petcare",
    "uid": "sa",
    "pwd": "YourPassword123",
    "driver": "{ODBC Driver 17 for SQL Server}",
    "trusted_connection": False,
}
```

Nếu dùng Windows Authentication thì đặt:

```python
DB_CONFIG = {
    "server": "localhost",
    "database": "petcare",
    "driver": "{ODBC Driver 17 for SQL Server}",
    "trusted_connection": True,
}
```

### 4. Chạy web

```powershell
python app_mssql.py
```

Mở trình duyệt:

```text
http://127.0.0.1:8000
```

Khi chạy lần đầu, ứng dụng tự tạo bảng theo `schema_mssql.sql` và thêm dữ liệu mẫu nếu bảng `users` đang rỗng.

## Tài khoản mẫu

Mật khẩu của tất cả tài khoản mẫu: `123456`

| Vai trò | Email |
|---|---|
| Khách hàng | `khach@example.com` |
| Nhân viên | `nhanvien@example.com` |
| Quản lý | `quanly@example.com` |

## Cách demo module quản lý lịch hẹn

### Luồng khách hàng

1. Đăng nhập bằng `khach@example.com`.
2. Vào **Đặt lịch**.
3. Chọn dịch vụ, nhập ngày giờ, tên thú cưng và xác nhận đặt lịch.
4. Vào **Lịch của tôi** để xem danh sách lịch.
5. Bấm **Xem** để xem chi tiết.
6. Nếu lịch còn trạng thái đã đặt, bấm **Hủy lịch hẹn** để hủy.

### Luồng nhân viên

1. Đăng nhập bằng `nhanvien@example.com`.
2. Vào **Kiểm tra lịch**.
3. Xem danh sách lịch hẹn của khách hàng.
4. Bấm **Xem** để xem chi tiết lịch hẹn.
5. Có thể bấm **Tạo hóa đơn** nếu muốn demo phần liên kết nghiệp vụ tại quầy.

## CSDL SQL Server

File thiết kế và tạo bảng:

```text
schema_mssql.sql
```

Các bảng chính:

- `users`
- `services`
- `appointments`
- `appointment_services`
- `invoices`
- `invoice_details`

Riêng module quản lý lịch hẹn dùng chủ yếu:

- `users` với vai trò khách hàng/nhân viên
- `services`
- `appointments`
- `appointment_services`

## SQLite để làm gì?

`app.py`, `schema.sql` và `data/petcare.db` là bản SQLite cũ để chạy nhanh khi máy không có SQL Server. Khi bảo vệ với yêu cầu CSDL SQL Server, không cần demo SQLite. Có thể giữ làm bản dự phòng, nhưng bản chính nên chạy bằng:

```powershell
python app_mssql.py
```
