-- SQL Server Schema for PetCare Web Application

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'NguoiDung')
CREATE TABLE NguoiDung (
    MaNguoiDung INT PRIMARY KEY IDENTITY(1,1),
    HoTen NVARCHAR(100),
    Email NVARCHAR(100),
    SDT NVARCHAR(15),
    DiaChi NVARCHAR(255),
    NgaySinh DATE
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'VaiTro')
CREATE TABLE VaiTro (
    MaVaiTro INT PRIMARY KEY IDENTITY(1,1),
    TenVaiTro NVARCHAR(50)
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'TaiKhoan')
CREATE TABLE TaiKhoan (
    MaTK INT PRIMARY KEY IDENTITY(1,1),
    MaNguoiDung INT,
    MaVaiTro INT,
    TenDangNhap NVARCHAR(50),
    MatKhau NVARCHAR(50),
    TrangThai NVARCHAR(30),
    FOREIGN KEY (MaNguoiDung) REFERENCES NguoiDung(MaNguoiDung),
    FOREIGN KEY (MaVaiTro) REFERENCES VaiTro(MaVaiTro)
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'KhachHang')
CREATE TABLE KhachHang (
    MaKH INT PRIMARY KEY IDENTITY(1,1),
    MaNguoiDung INT UNIQUE,
    FOREIGN KEY (MaNguoiDung) REFERENCES NguoiDung(MaNguoiDung)
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'NhanVien')
CREATE TABLE NhanVien (
    MaNV INT PRIMARY KEY IDENTITY(1,1),
    MaNguoiDung INT UNIQUE,
    FOREIGN KEY (MaNguoiDung) REFERENCES NguoiDung(MaNguoiDung)
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'QuanLy')
CREATE TABLE QuanLy (
    MaQL INT PRIMARY KEY IDENTITY(1,1),
    MaNguoiDung INT UNIQUE,
    FOREIGN KEY (MaNguoiDung) REFERENCES NguoiDung(MaNguoiDung)
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PhienDangNhap')
CREATE TABLE PhienDangNhap (
    MaPhien INT PRIMARY KEY IDENTITY(1,1),
    MaTK INT,
    ThoiGianDangXuat DATETIME,
    ThoiGianDangNhap DATETIME,
    TrangThai NVARCHAR(50),
    FOREIGN KEY (MaTK) REFERENCES TaiKhoan(MaTK)
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'services')
CREATE TABLE services (
    id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX),
    price DECIMAL(10, 0) NOT NULL CHECK (price >= 0),
    status NVARCHAR(50) NOT NULL DEFAULT 'active'
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'appointments')
CREATE TABLE appointments (
    id INT PRIMARY KEY IDENTITY(1,1),
    customer_id INT NOT NULL,
    pet_name NVARCHAR(255) NOT NULL,
    pet_type NVARCHAR(255) NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status NVARCHAR(50) NOT NULL DEFAULT 'booked',
    estimated_total DECIMAL(10, 0) NOT NULL DEFAULT 0,
    note NVARCHAR(MAX),
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (customer_id) REFERENCES KhachHang(MaKH)
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'appointment_services')
CREATE TABLE appointment_services (
    appointment_id INT NOT NULL,
    service_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price DECIMAL(10, 0) NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (appointment_id, service_id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id)
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'invoices')
CREATE TABLE invoices (
    id INT PRIMARY KEY IDENTITY(1,1),
    appointment_id INT NOT NULL UNIQUE,
    staff_id INT NOT NULL,
    total_amount DECIMAL(10, 0) NOT NULL CHECK (total_amount >= 0),
    payment_status NVARCHAR(50) NOT NULL DEFAULT 'paid',
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (appointment_id) REFERENCES appointments(id),
    FOREIGN KEY (staff_id) REFERENCES NhanVien(MaNV)
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'invoice_details')
CREATE TABLE invoice_details (
    id INT PRIMARY KEY IDENTITY(1,1),
    invoice_id INT NOT NULL,
    service_name NVARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 0) NOT NULL,
    line_total DECIMAL(10, 0) NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);
