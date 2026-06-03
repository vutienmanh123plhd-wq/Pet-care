-- SQL Server Schema for PetCare Web Application

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'users')
CREATE TABLE users (
    id INT PRIMARY KEY IDENTITY(1,1),
    full_name NVARCHAR(255) NOT NULL,
    email NVARCHAR(255) NOT NULL UNIQUE,
    phone NVARCHAR(20),
    address NVARCHAR(255),
    role NVARCHAR(50) NOT NULL CHECK (role IN ('customer', 'staff', 'manager')),
    password_hash NVARCHAR(255) NOT NULL,
    status NVARCHAR(50) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT GETDATE()
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
    FOREIGN KEY (customer_id) REFERENCES users(id)
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
    FOREIGN KEY (staff_id) REFERENCES users(id)
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
