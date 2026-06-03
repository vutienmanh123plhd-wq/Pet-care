## Cách chạy

### Phiên bản SQLite (mặc định)

```powershell
cd C:\Users\quang\Desktop\btl_cnpm\petcare_web
python app.py
```

### Phiên bản SQL Server

#### 1. Cài đặt dependencies

```powershell
pip install -r requirements_mssql.txt
```

#### 2. Cấu hình kết nối SQL Server

Chỉnh sửa file `config.py`:

```python
DB_CONFIG = {
    "server": "localhost",          # Tên server hoặc IP
    "database": "petcare",          # Tên database
    "uid": "sa",                    # Tên tài khoản (SQL authentication)
    "pwd": "YourPassword123",       # Mật khẩu
    "driver": "{ODBC Driver 17 for SQL Server}",
    "trusted_connection": False,    # False cho SQL authentication, True cho Windows auth
}

# Hoặc cho Windows Authentication:
DB_CONFIG = {
    "server": "localhost",
    "database": "petcare",
    "driver": "{ODBC Driver 17 for SQL Server}",
    "trusted_connection": True,
}
```

#### 3. Chạy ứng dụng

```powershell
python app_mssql.py
```

Mở trình duyệt:

```text
http://127.0.0.1:8000
```

#### Lưu ý quan trọng

- **ODBC Driver**: Cần cài ODBC Driver 17 for SQL Server trên máy
  - Download: https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server
  - Hoặc dùng `choco install odbc-driver-17-sql-server` (Chocolatey)

- **Database**: Phải tạo database `petcare` trước khi chạy ứng dụng

- **SQL Server**: Phải có SQL Server instance đang chạy

## Tài khoản mẫu

Mật khẩu của tất cả tài khoản mẫu: `123456`

| Vai trò    | Email                  |
| ---------- | ---------------------- |
| Khách hàng | `khach@example.com`    |
| Nhân viên  | `nhanvien@example.com` |
| Quản lý    | `quanly@example.com`   |

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
