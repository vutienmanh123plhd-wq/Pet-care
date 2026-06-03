# Hướng dẫn thiết lập SQL Server cho PetCare

## Bước 1: Cài đặt SQL Server

### Windows

- Download: https://www.microsoft.com/en-us/sql-server/sql-server-downloads
- Chọn SQL Server Developer Edition (miễn phí)
- Cài đặt và lưu tên instance

### Bằng Docker

```bash
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=YourPassword123" -p 1433:1433 -d mcr.microsoft.com/mssql/server:latest
```

## Bước 2: Cài đặt ODBC Driver

### Windows

- Download: https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server
- Hoặc dùng Chocolatey:

```powershell
choco install odbc-driver-17-sql-server
```

## Bước 3: Tạo Database

### Sử dụng SQL Server Management Studio (SSMS)

1. Mở SSMS
2. Kết nối với server
3. Right-click "Databases" → "New Database"
4. Tên: `petcare`
5. Click OK

### Hoặc dùng PowerShell/SQL command

```sql
CREATE DATABASE petcare;
```

## Bước 4: Cấu hình PetCare

Sửa `config.py`:

```python
DB_CONFIG = {
    "server": "localhost",  # hoặc tên instance
    "database": "petcare",
    "uid": "sa",            # hoặc tên user của bạn
    "pwd": "YourPassword123",
    "driver": "{ODBC Driver 17 for SQL Server}",
    "trusted_connection": False,
}
```

## Bước 5: Cài đặt Python Dependencies

```powershell
pip install -r requirements.txt
```

## Bước 6: Chạy ứng dụng

```powershell
python app.py
```

## Troubleshooting

### Lỗi: "pyodbc.InterfaceError: ('IM002', '[IM002]...')"

- **Nguyên nhân**: ODBC Driver không được cài đặt
- **Giải pháp**: Cài đặt ODBC Driver 17 for SQL Server

### Lỗi: "pyodbc.Error: ('28000'...)"

- **Nguyên nhân**: Sai username hoặc password
- **Giải pháp**: Kiểm tra lại credentials trong `config.py`

### Lỗi: "pyodbc.ProgrammingError: ('42S02'...)"

- **Nguyên nhân**: Database `petcare` không tồn tại
- **Giải pháp**: Tạo database `petcare` trước

### Lỗi: "pyodbc.OperationalError: ('HYT00'...)"

- **Nguyên nhân**: Không kết nối được SQL Server
- **Giải pháp**: Kiểm tra server name/IP trong `config.py`

## Connection String Examples

### SQL Authentication

```
Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=petcare;UID=sa;PWD=password;
```

### Windows Authentication

```
Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=petcare;Trusted_Connection=yes;
```

### Remote Server

```
Driver={ODBC Driver 17 for SQL Server};Server=192.168.1.100;Database=petcare;UID=sa;PWD=password;Port=1433;
```

### Named Instance

```
Driver={ODBC Driver 17 for SQL Server};Server=COMPUTER\SQLEXPRESS;Database=petcare;UID=sa;PWD=password;
```
