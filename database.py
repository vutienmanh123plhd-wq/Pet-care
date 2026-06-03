# -*- coding: utf-8 -*-
from pathlib import Path
import hashlib
import pyodbc

from config import DB_CONFIG

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schema.sql"


def get_connection_string():
    if DB_CONFIG.get("trusted_connection"):
        return (
            f"Driver={DB_CONFIG['driver']};"
            f"Server={DB_CONFIG['server']};"
            f"Database={DB_CONFIG['database']};"
            "Trusted_Connection=yes;"
        )
    return (
        f"Driver={DB_CONFIG['driver']};"
        f"Server={DB_CONFIG['server']};"
        f"Database={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['uid']};"
        f"PWD={DB_CONFIG['pwd']};"
    )


def password_hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class Connection:
    """Small SQL Server connection wrapper used by the backend."""

    def __init__(self, conn_string):
        self.conn = pyodbc.connect(conn_string)

    def execute(self, sql, params=None):
        cursor = self.conn.cursor()
        if params is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, params)
        return cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()


def db():
    return Connection(get_connection_string())


def get_id(conn, sql, params):
    row = conn.execute(sql, params).fetchone()
    return int(row[0]) if row else None


def ensure_user(conn, full_name, email, phone, address, role):
    user_id = get_id(conn, "SELECT id FROM users WHERE email = ?", (email,))
    if user_id:
        return user_id

    cursor = conn.execute(
        """
        INSERT INTO users(full_name, email, phone, address, role, password_hash)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (full_name, email, phone, address, role, password_hash("123456")),
    )
    return int(cursor.fetchone()[0])


def ensure_service(conn, name, description, price):
    service_id = get_id(conn, "SELECT id FROM services WHERE name = ?", (name,))
    if service_id:
        return service_id

    cursor = conn.execute(
        """
        INSERT INTO services(name, description, price)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?)
        """,
        (name, description, price),
    )
    return int(cursor.fetchone()[0])


def ensure_appointment(conn, customer_id, pet_name, pet_type, date, time, status, total, note):
    appointment_id = get_id(
        conn,
        """
        SELECT id
        FROM appointments
        WHERE customer_id = ? AND pet_name = ? AND appointment_date = ? AND appointment_time = ?
        """,
        (customer_id, pet_name, date, time),
    )
    if appointment_id:
        return appointment_id

    cursor = conn.execute(
        """
        INSERT INTO appointments(customer_id, pet_name, pet_type, appointment_date,
                                 appointment_time, status, estimated_total, note)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (customer_id, pet_name, pet_type, date, time, status, total, note),
    )
    return int(cursor.fetchone()[0])


def ensure_appointment_service(conn, appointment_id, service_id, quantity, unit_price):
    exists = conn.execute(
        """
        SELECT 1
        FROM appointment_services
        WHERE appointment_id = ? AND service_id = ?
        """,
        (appointment_id, service_id),
    ).fetchone()
    if exists:
        return

    conn.execute(
        """
        INSERT INTO appointment_services(appointment_id, service_id, quantity, unit_price)
        VALUES (?, ?, ?, ?)
        """,
        (appointment_id, service_id, quantity, unit_price),
    )


def ensure_invoice(conn, appointment_id, staff_id, total_amount, details):
    invoice_id = get_id(conn, "SELECT id FROM invoices WHERE appointment_id = ?", (appointment_id,))
    if not invoice_id:
        cursor = conn.execute(
            """
            INSERT INTO invoices(appointment_id, staff_id, total_amount)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?)
            """,
            (appointment_id, staff_id, total_amount),
        )
        invoice_id = int(cursor.fetchone()[0])

    detail_count = conn.execute(
        "SELECT COUNT(*) FROM invoice_details WHERE invoice_id = ?",
        (invoice_id,),
    ).fetchone()[0]
    if detail_count:
        return invoice_id

    for service_name, quantity, unit_price in details:
        conn.execute(
            """
            INSERT INTO invoice_details(invoice_id, service_name, quantity, unit_price, line_total)
            VALUES (?, ?, ?, ?, ?)
            """,
            (invoice_id, service_name, quantity, unit_price, quantity * unit_price),
        )
    return invoice_id


def seed_demo_data(conn):
    users = {
        "khach@example.com": ensure_user(conn, "Nguyễn Văn A", "khach@example.com", "0345345632", "Hà Nội", "customer"),
        "chau@example.com": ensure_user(conn, "Phạm Minh Châu", "chau@example.com", "0933445566", "Hà Nội", "customer"),
        "an@example.com": ensure_user(conn, "Hoàng Bảo An", "an@example.com", "0988776655", "Hải Phòng", "customer"),
        "ha@example.com": ensure_user(conn, "Mai Thu Hà", "ha@example.com", "0977123123", "Đà Nẵng", "customer"),
        "nhanvien@example.com": ensure_user(conn, "Trần Thị Nhân", "nhanvien@example.com", "0901122334", "Cửa hàng", "staff"),
        "quanly@example.com": ensure_user(conn, "Lê Văn Quản", "quanly@example.com", "0919988776", "Cửa hàng", "manager"),
    }

    service_defs = [
        ("Tắm thú cưng", "Tắm, sấy và vệ sinh cơ bản cho thú cưng.", 200000),
        ("Mát xa thư giãn", "Mát xa nhẹ giúp thú cưng thư giãn.", 250000),
        ("Cắt tỉa lông", "Cắt tỉa tạo dáng và vệ sinh lông.", 300000),
        ("Vệ sinh tai móng", "Vệ sinh tai, cắt móng và kiểm tra cơ bản.", 120000),
        ("Khám sức khỏe cơ bản", "Kiểm tra tổng quát tình trạng sức khỏe thú cưng.", 180000),
        ("Tiêm phòng", "Tiêm phòng theo lịch và ghi nhận thông tin theo dõi.", 350000),
        ("Lưu trú theo ngày", "Chăm sóc và lưu trú thú cưng tại cửa hàng.", 150000),
    ]
    services = {name: ensure_service(conn, name, description, price) for name, description, price in service_defs}
    service_prices = {name: price for name, _, price in service_defs}

    appointments = [
        ("khach@example.com", "Bun", "Thỏ", "2026-06-10", "14:00", "booked", "Tắm và vệ sinh tai móng.", ["Tắm thú cưng", "Vệ sinh tai móng"]),
        ("khach@example.com", "Milu", "Chó", "2026-06-12", "09:30", "booked", "Cắt tỉa lông mùa hè.", ["Cắt tỉa lông"]),
        ("chau@example.com", "Miu", "Mèo", "2026-06-15", "10:00", "cancelled", "Khách đã hủy lịch trước giờ hẹn.", ["Tắm thú cưng"]),
        ("an@example.com", "Lucky", "Chó", "2026-06-08", "15:30", "paid", "Đã hoàn tất dịch vụ và thanh toán.", ["Tắm thú cưng", "Vệ sinh tai móng"]),
        ("ha@example.com", "Bông", "Mèo", "2026-06-20", "08:00", "booked", "Khám sức khỏe định kỳ.", ["Khám sức khỏe cơ bản"]),
        ("khach@example.com", "Ken", "Chó", "2026-05-30", "16:00", "paid", "Đã hoàn tất tắm và cắt tỉa.", ["Tắm thú cưng", "Cắt tỉa lông"]),
    ]

    staff_id = users["nhanvien@example.com"]
    for email, pet_name, pet_type, date, time, status, note, service_names in appointments:
        details = [(name, 1, service_prices[name]) for name in service_names]
        total = sum(quantity * unit_price for _, quantity, unit_price in details)
        appointment_id = ensure_appointment(
            conn,
            users[email],
            pet_name,
            pet_type,
            date,
            time,
            status,
            total,
            note,
        )

        for service_name, quantity, unit_price in details:
            ensure_appointment_service(conn, appointment_id, services[service_name], quantity, unit_price)

        if status == "paid":
            ensure_invoice(conn, appointment_id, staff_id, total, details)


def init_db():
    with db() as conn:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        for statement in schema_sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(statement)

        seed_demo_data(conn)
