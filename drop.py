from database import db

tables = [
    'invoice_details', 'invoices', 'appointment_services', 'appointments', 'services', 
    'PhienDangNhap', 'KhachHang', 'NhanVien', 'QuanLy', 'TaiKhoan', 'VaiTro', 'NguoiDung', 'users'
]

with db() as conn:
    for t in tables:
        try:
            conn.execute(f"DROP TABLE {t}")
            print(f"Dropped {t}")
        except Exception as e:
            pass
