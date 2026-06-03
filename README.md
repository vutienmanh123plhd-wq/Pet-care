# PetCare Web - Module quản lý lịch hẹn

Project demo theo đề tài **Hệ thống quản lý cửa hàng chăm sóc thú cưng** trong `BTL_NMCNPM_N09.docx`.

Project hiện chỉ dùng **SQL Server** cho phần cơ sở dữ liệu.

## Chức năng module quản lý lịch hẹn

- Khách hàng đặt lịch hẹn.
- Khách hàng xem lịch hẹn, xem chi tiết, hủy lịch.
- Nhân viên kiểm tra lịch hẹn khách hàng, tìm kiếm và xem chi tiết.

## Cách chạy

### 1. Cài thư viện

```powershell
cd C:\Users\quang\Desktop\btl_cnpm\petcare_web
pip install -r requirements.txt
```

### 2. Tạo database SQL Server

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

Nếu dùng Windows Authentication:

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
python app.py
```

Mở trình duyệt:

```text
http://127.0.0.1:8000
```

Khi chạy, ứng dụng tự tạo bảng theo `schema.sql` và tự bổ sung dữ liệu mẫu nếu dữ liệu đó chưa tồn tại.

## Tài khoản mẫu

Mật khẩu của tất cả tài khoản mẫu: `123456`

| Vai trò | Email |
|---|---|
| Khách hàng | `khach@example.com` |
| Nhân viên | `nhanvien@example.com` |
| Quản lý | `quanly@example.com` |

## Dữ liệu mẫu

Ứng dụng có sẵn một số dữ liệu để demo module quản lý lịch hẹn:

| Nhóm dữ liệu | Ví dụ |
|---|---|
| Khách hàng | `khach@example.com`, `chau@example.com`, `an@example.com`, `ha@example.com` |
| Dịch vụ | Tắm thú cưng, Cắt tỉa lông, Vệ sinh tai móng, Khám sức khỏe cơ bản, Tiêm phòng |
| Lịch hẹn đã đặt | Bun, Milu, Bông |
| Lịch hẹn đã hủy | Miu |
| Lịch hẹn đã thanh toán | Lucky, Ken |
| Hóa đơn mẫu | Tự sinh cho các lịch hẹn đã thanh toán |

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

File tạo bảng:

```text
schema.sql
```

File xử lý database ở backend:

```text
database.py
```

`database.py` phụ trách kết nối SQL Server, chạy `schema.sql`, tự thêm dữ liệu mẫu và cung cấp hàm `db()` cho các chức năng trong `app.py`.

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
