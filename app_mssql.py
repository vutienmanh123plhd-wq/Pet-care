# -*- coding: utf-8 -*-
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse
import hashlib
import html
import mimetypes
import secrets
import pyodbc
from config import DB_CONFIG, HOST, PORT

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schema_mssql.sql"
STATIC_DIR = ROOT / "static"
SESSIONS = {}

# Build connection string for SQL Server
def get_connection_string():
    if DB_CONFIG.get("trusted_connection"):
        return f"Driver={DB_CONFIG['driver']};Server={DB_CONFIG['server']};Database={DB_CONFIG['database']};Trusted_Connection=yes;"
    else:
        return f"Driver={DB_CONFIG['driver']};Server={DB_CONFIG['server']};Database={DB_CONFIG['database']};UID={DB_CONFIG['uid']};PWD={DB_CONFIG['pwd']};"

def escape(value):
    return html.escape("" if value is None else str(value), quote=True)

def password_hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

class Row:
    """Wrapper to mimic sqlite3.Row for SQL Server"""
    def __init__(self, columns, values):
        self.columns = columns
        self.values = values
    
    def __getitem__(self, key):
        if isinstance(key, int):
            return self.values[key]
        return self.values[self.columns.index(key)]
    
    def __getattr__(self, name):
        try:
            return self[name]
        except ValueError:
            raise AttributeError(f"No column named {name}")

class Connection:
    """Wrapper for SQL Server connection to mimic sqlite3 interface"""
    def __init__(self, conn_string):
        self.conn = pyodbc.connect(conn_string)
        self.conn.setdecoding(pyodbc.SQL_CHAR, 'utf-8')
        self.conn.setdecoding(pyodbc.SQL_WCHAR, 'utf-8')
    
    def execute(self, sql, params=None):
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
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
    """Get database connection"""
    conn_string = get_connection_string()
    return Connection(conn_string)

def init_db():
    """Initialize database schema and demo data"""
    try:
        with db() as conn:
            schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
            for statement in schema_sql.split(';'):
                statement = statement.strip()
                if statement:
                    conn.execute(statement)

            cursor = conn.execute("SELECT COUNT(*) as cnt FROM users")
            result = cursor.fetchone()
            count = result[0] if result else 0
            
            if count == 0:
                # Insert demo users
                users = [
                    ("Nguyễn Văn A", "khach@example.com", "0345345632", "Hà Nội", "customer"),
                    ("Trần Thị Nhân", "nhanvien@example.com", "0901122334", "Cửa hàng", "staff"),
                    ("Lê Văn Quản", "quanly@example.com", "0919988776", "Cửa hàng", "manager"),
                ]
                for full_name, email, phone, address, role in users:
                    conn.execute(
                        """
                        INSERT INTO users(full_name, email, phone, address, role, password_hash)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (full_name, email, phone, address, role, password_hash("123456")),
                    )
                
                # Insert demo services
                services = [
                    ("Tắm thú cưng", "Tắm, sấy và vệ sinh cơ bản cho thú cưng.", 200000),
                    ("Mát xa thư giãn", "Mát xa nhẹ giúp thú cưng thư giãn.", 250000),
                    ("Cắt tỉa lông", "Cắt tỉa tạo dáng và vệ sinh lông.", 300000),
                    ("Vệ sinh tai móng", "Vệ sinh tai, cắt móng và kiểm tra cơ bản.", 120000),
                ]
                for name, description, price in services:
                    conn.execute(
                        "INSERT INTO services(name, description, price) VALUES (?, ?, ?)",
                        (name, description, price),
                    )
                
                # Insert demo appointment
                conn.execute(
                    """
                    INSERT INTO appointments(customer_id, pet_name, pet_type, appointment_date,
                                           appointment_time, estimated_total, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (1, "Bun", "Rabbit", "2024-06-10", "14:00", 200000, "Tắm cơ bản"),
                )
                
                # Insert demo appointment services
                conn.execute(
                    """
                    INSERT INTO appointment_services(appointment_id, service_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (1, 1, 1, 200000),
                )
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

def service_summary(conn, appointment_id):
    rows = conn.execute(
        """
        SELECT s.name, ads.quantity, ads.unit_price
        FROM appointment_services ads
        JOIN services s ON s.id = ads.service_id
        WHERE ads.appointment_id = ?
        ORDER BY s.name
        """,
        (appointment_id,),
    ).fetchall()
    if not rows:
        return "Chưa có dịch vụ"
    return ", ".join(f"{row[0]} x{row[1]}" for row in rows)

def current_user(handler):
    raw_cookie = handler.headers.get("Cookie", "")
    jar = cookies.SimpleCookie(raw_cookie)
    sid = jar.get("sid")
    if not sid:
        return None
    user_id = SESSIONS.get(sid.value)
    if not user_id:
        return None
    with db() as conn:
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return {col[0]: row[i] for i, col in enumerate(cursor.description)}
        return None

def layout(title, content, user=None, active="", flash=""):
    nav_items = []
    if user:
        role = user["role"]
        nav_items = [
            ("Tổng quan", "/dashboard", "dashboard"),
            ("Dịch vụ", "/services", "services"),
        ]
        if role == "customer":
            nav_items += [
                ("Đặt lịch", "/appointments/new", "book"),
                ("Lịch của tôi", "/appointments", "appointments"),
            ]
        if role in ("staff", "manager"):
            nav_items += [
                ("Kiểm tra lịch", "/appointments", "appointments"),
                ("Hóa đơn", "/invoices", "invoices"),
            ]
        if role == "manager":
            nav_items += [("Thống kê", "/stats", "stats")]
        nav_items += [("Đăng xuất", "/logout", "logout")]
    
    sidebar = ""
    if nav_items:
        links = "\n".join(
            f'<a class="{ "active" if key == active else "" }" href="{href}">{label}</a>'
            for label, href, key in nav_items
        )
        sidebar = f'<aside class="sidebar">{links}</aside>'
    
    user_pill = ""
    if user:
        role_map = {"customer": "Khách", "staff": "Nhân viên", "manager": "Quản lý"}
        user_pill = f'<div class="user-pill">{escape(user["full_name"])} - {role_map.get(user["role"], user["role"])}</div>'
    
    topbar = f"""
    <header class="topbar">
        <div class="brand">Hệ thống quản lý cửa hàng chăm sóc thú cưng</div>
        {user_pill}
    </header>
    """
    flash_html = f'<div class="flash">{escape(flash)}</div>' if flash else ""
    body = f"""
    <!doctype html>
    <html lang="vi">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{escape(title)}</title>
        <link rel="stylesheet" href="/static/styles.css">
    </head>
    <body>
        {topbar}
        <main class="layout">
            {sidebar}
            <section class="content">
                {flash_html}
                {content}
            </section>
        </main>
    </body>
    </html>
    """
    return body

def money(value):
    return f"{int(value):,.0f}đ".replace(",", ".")

def status_label(status):
    return {
        "booked": "Đã đặt",
        "cancelled": "Đã hủy",
        "paid": "Đã thanh toán",
    }.get(status, status)

def status_badge(status):
    cls = {"booked": "booked", "cancelled": "cancelled", "paid": "paid"}.get(status, "booked")
    return f'<span class="badge {cls}">{escape(status_label(status))}</span>'

class PetCareHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.home()
        elif path == "/login":
            self.login_page()
        elif path == "/register":
            self.register_page()
        elif path == "/dashboard":
            self.dashboard()
        elif path == "/services":
            self.services_page()
        elif path.startswith("/appointments"):
            if path == "/appointments/new":
                self.create_appointment_page()
            elif path.startswith("/appointments/"):
                self.appointment_detail(path.rsplit("/", 1)[-1])
            else:
                self.appointments()
        elif path == "/invoices":
            self.invoices()
        elif path == "/stats":
            self.stats()
        elif path == "/logout":
            self.logout()
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == "/login":
            self.login_action()
        elif self.path == "/register":
            self.register_action()
        elif self.path == "/appointments/new":
            self.create_appointment()
        elif self.path == "/appointments/cancel":
            self.cancel_appointment()
        elif self.path == "/services/manage":
            self.manage_services()
        elif self.path == "/invoices":
            self.create_invoice()
        else:
            self.send_error(404)
    
    def send_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    
    def redirect(self, path, cookie=None):
        self.send_response(302)
        self.send_header("Location", path)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
    
    def read_form(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        return parse_qs(body)
    
    def query_msg(self):
        parsed = urlparse(self.path)
        return parse_qs(parsed.query).get("msg", [""])[0]
    
    def require_user(self):
        user = current_user(self)
        if not user:
            self.redirect("/login?msg=" + quote("Vui lòng đăng nhập"))
            return None
        return user
    
    def require_roles(self, roles):
        user = self.require_user()
        if user and user["role"] not in roles:
            self.send_html(layout("Lỗi", "<p>Bạn không có quyền truy cập trang này.</p>", user))
            return None
        return user
    
    def home(self):
        user = current_user(self)
        if user:
            return self.redirect("/dashboard")
        content = """
        <div class="hero">
            <h1>Hệ thống quản lý cửa hàng chăm sóc thú cưng</h1>
            <p class="muted">Website demo theo đề tài BTL_NMCNPM_N09: quản lý tài khoản, dịch vụ, lịch hẹn, hóa đơn và thống kê cơ bản.</p>
            <div class="grid grid-3">
                <div class="card stat"><span>Khách hàng</span><strong>Đặt lịch</strong><p>Xem và hủy lịch đã đặt.</p></div>
                <div class="card stat"><span>Nhân viên</span><strong>Kiểm tra</strong><p>Tra cứu lịch hẹn và tạo hóa đơn.</p></div>
                <div class="card stat"><span>Quản lý</span><strong>Thống kê</strong><p>Quản lý dịch vụ và doanh thu.</p></div>
            </div>
            <div class="actions">
                <a class="btn" href="/login">Đăng nhập</a>
                <a class="btn secondary" href="/register">Đăng ký khách hàng</a>
            </div>
        </div>
        """
        self.send_html(layout("Trang chủ", content))
    
    def login_page(self):
        content = f"""
        <div class="hero">
            <h1>Đăng nhập</h1>
            <div class="demo-accounts">
                <h3>Tài khoản Demo</h3>
                <div class="demo-list">
                    <div class="demo-item">
                        <strong>Khách hàng</strong><br>
                        Email: khach@example.com<br>
                        Mật khẩu: 123456
                    </div>
                    <div class="demo-item">
                        <strong>Nhân viên</strong><br>
                        Email: nhanvien@example.com<br>
                        Mật khẩu: 123456
                    </div>
                    <div class="demo-item">
                        <strong>Quản lý</strong><br>
                        Email: quanly@example.com<br>
                        Mật khẩu: 123456
                    </div>
                </div>
            </div>
            <form method="post" action="/login">
                <div class="form-row">
                    <div><label>Email</label><input name="email" type="email" required placeholder="khach@example.com"></div>
                    <div><label>Mật khẩu</label><input name="password" type="password" required placeholder="123456"></div>
                </div>
                <div class="actions">
                    <button class="btn" type="submit">Đăng nhập</button>
                    <a class="btn secondary" href="/register">Đăng ký khách hàng</a>
                </div>
            </form>
        </div>
        """
        self.send_html(layout("Đăng nhập", content, flash=self.query_msg()))
    
    def login_action(self):
        form = self.read_form()
        email = form.get("email", [""])[0].strip().lower()
        password = form.get("password", [""])[0]
        with db() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE email = ? AND status = 'active'", (email,))
            row = cursor.fetchone()
            if row:
                user = {col[0]: row[i] for i, col in enumerate(cursor.description)}
            else:
                user = None
        
        if not user or user["password_hash"] != password_hash(password):
            return self.redirect("/login?msg=" + quote("Email hoặc mật khẩu không đúng."))
        
        sid = secrets.token_urlsafe(32)
        SESSIONS[sid] = user["id"]
        self.redirect("/dashboard", f"sid={sid}; Path=/; HttpOnly; SameSite=Lax")
    
    def register_page(self):
        content = """
        <div class="hero">
            <h1>Đăng ký khách hàng</h1>
            <form method="post" action="/register">
                <div class="form-row">
                    <div><label>Họ tên</label><input name="full_name" type="text" required></div>
                    <div><label>Email</label><input name="email" type="email" required></div>
                </div>
                <div class="form-row">
                    <div><label>Điện thoại</label><input name="phone" type="tel" required></div>
                    <div><label>Địa chỉ</label><input name="address" type="text" required></div>
                </div>
                <div class="form-row">
                    <div><label>Mật khẩu</label><input name="password" type="password" required></div>
                    <div><label>Xác nhận mật khẩu</label><input name="confirm" type="password" required></div>
                </div>
                <div class="actions">
                    <button class="btn" type="submit">Đăng ký</button>
                    <a class="btn secondary" href="/login">Đã có tài khoản?</a>
                </div>
            </form>
        </div>
        """
        self.send_html(layout("Đăng ký", content, flash=self.query_msg()))
    
    def register_action(self):
        form = self.read_form()
        full_name = form.get("full_name", [""])[0].strip()
        email = form.get("email", [""])[0].strip().lower()
        phone = form.get("phone", [""])[0].strip()
        address = form.get("address", [""])[0].strip()
        password = form.get("password", [""])[0]
        confirm = form.get("confirm", [""])[0]
        
        if not all([full_name, email, phone, address, password]):
            return self.redirect("/register?msg=" + quote("Vui lòng điền tất cả thông tin."))
        if password != confirm:
            return self.redirect("/register?msg=" + quote("Mật khẩu không khớp."))
        
        with db() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO users(full_name, email, phone, address, role, password_hash)
                    VALUES (?, ?, ?, ?, 'customer', ?)
                    """,
                    (full_name, email, phone, address, password_hash(password)),
                )
            except Exception:
                return self.redirect("/register?msg=" + quote("Email đã được sử dụng."))
        
        self.redirect("/login?msg=" + quote("Đăng ký thành công. Vui lòng đăng nhập."))
    
    def dashboard(self):
        user = self.require_user()
        if not user:
            return
        content = f"""
        <div class="hero">
            <h1>Xin chào, {escape(user['full_name'])}</h1>
            <p class="muted">Chào mừng bạn đến với hệ thống quản lý cửa hàng chăm sóc thú cưng.</p>
        </div>
        """
        self.send_html(layout("Tổng quan", content, user, "dashboard"))
    
    def services_page(self):
        user = self.require_user()
        if not user:
            return
        
        with db() as conn:
            cursor = conn.execute("SELECT * FROM services WHERE status = 'active' ORDER BY name")
            rows = cursor.fetchall()
        
        body_rows = "".join(
            f"""
            <tr>
                <td>{escape(row[1])}</td>
                <td>{escape(row[2]) if row[2] else ""}</td>
                <td>{money(row[3])}</td>
            </tr>
            """
            for row in rows
        )
        
        content = f"""
        <div class="card">
            <h1>Dịch vụ</h1>
            <table>
                <thead><tr><th>Tên dịch vụ</th><th>Mô tả</th><th>Giá</th></tr></thead>
                <tbody>{body_rows if body_rows else '<tr><td colspan="3">Chưa có dịch vụ nào.</td></tr>'}</tbody>
            </table>
        </div>
        """
        self.send_html(layout("Dịch vụ", content, user, "services"))
    
    def create_appointment_page(self):
        user = self.require_roles(("customer",))
        if not user:
            return
        
        with db() as conn:
            cursor = conn.execute("SELECT id, name, price FROM services WHERE status = 'active' ORDER BY name")
            services = cursor.fetchall()
        
        service_options = "".join(
            f'<label class="service-option"><input type="checkbox" name="service_id" value="{s[0]}"> {escape(s[1])} - {money(s[2])}</label>'
            for s in services
        )
        
        content = f"""
        <div class="hero">
            <h1>Đặt lịch hẹn</h1>
            <form method="post" action="/appointments/new">
                <div class="form-row">
                    <div><label>Tên thú cưng</label><input name="pet_name" type="text" required></div>
                    <div><label>Loại thú cưng</label><input name="pet_type" type="text" required></div>
                </div>
                <div class="form-row">
                    <div><label>Ngày hẹn</label><input name="appointment_date" type="date" required></div>
                    <div><label>Giờ hẹn</label><input name="appointment_time" type="time" required></div>
                </div>
                <label>Dịch vụ cần sử dụng</label>
                <div class="service-list">
                    {service_options}
                </div>
                <label>Ghi chú</label>
                <textarea name="note" placeholder="Ghi chú thêm..."></textarea>
                <div class="actions">
                    <button class="btn" type="submit">Đặt lịch</button>
                    <a class="btn secondary" href="/appointments">Hủy</a>
                </div>
            </form>
        </div>
        """
        self.send_html(layout("Đặt lịch", content, user, "book", self.query_msg()))
    
    def create_appointment(self):
        user = self.require_roles(("customer",))
        if not user:
            return
        form = self.read_form()
        service_ids = [int(x) for x in form.get("service_id", []) if x.isdigit()]
        pet_name = form.get("pet_name", [""])[0].strip()
        pet_type = form.get("pet_type", [""])[0].strip()
        date = form.get("appointment_date", [""])[0]
        time = form.get("appointment_time", [""])[0]
        note = form.get("note", [""])[0].strip()
        
        if not service_ids:
            return self.redirect("/appointments/new?msg=" + quote("Vui lòng chọn ít nhất một dịch vụ."))
        
        with db() as conn:
            placeholders = ",".join("?" * len(service_ids))
            cursor = conn.execute(f"SELECT * FROM services WHERE id IN ({placeholders}) AND status = 'active'", service_ids)
            rows = cursor.fetchall()
            
            if len(rows) != len(service_ids):
                return self.redirect("/appointments/new?msg=" + quote("Dịch vụ không hợp lệ."))
            
            total = sum(row[3] for row in rows)
            cursor = conn.execute(
                """
                INSERT INTO appointments(customer_id, pet_name, pet_type, appointment_date,
                                         appointment_time, estimated_total, note)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user["id"], pet_name, pet_type, date, time, total, note),
            )
            appointment_id = cursor.fetchone()[0]
            
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO appointment_services(appointment_id, service_id, quantity, unit_price)
                    VALUES (?, ?, 1, ?)
                    """,
                    (int(appointment_id), row[0], row[3]),
                )
        
        self.redirect("/appointments?msg=" + quote("Đặt lịch hẹn thành công."))
    
    def appointments(self):
        user = self.require_user()
        if not user:
            return
        
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query).get("q", [""])[0].strip()
        
        with db() as conn:
            if user["role"] == "customer":
                cursor = conn.execute(
                    """
                    SELECT a.id, a.pet_name, a.pet_type, a.appointment_date, a.appointment_time,
                           a.status, a.estimated_total
                    FROM appointments a
                    WHERE a.customer_id = ?
                    ORDER BY a.appointment_date DESC
                    """,
                    (user["id"],)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT a.id, a.pet_name, a.pet_type, a.appointment_date, a.appointment_time,
                           a.status, a.estimated_total
                    FROM appointments a
                    ORDER BY a.appointment_date DESC
                    """
                )
            rows = cursor.fetchall()
        
        body_rows = "".join(
            f"""
            <tr>
                <td>#{row[0]}</td>
                <td>{escape(row[1])}<br><span class="muted">{escape(row[2])}</span></td>
                <td>{row[3]} {row[4]}</td>
                <td>{money(row[6])}</td>
                <td>{status_badge(row[5])}</td>
                <td><a class="btn secondary" href="/appointments/{row[0]}">Xem</a></td>
            </tr>
            """
            for row in rows
        )
        
        content = f"""
        <div class="card">
            <h1>Lịch hẹn</h1>
            <table>
                <thead><tr><th>Mã</th><th>Thú cưng</th><th>Ngày giờ</th><th>Tổng tiền</th><th>Trạng thái</th><th>Hành động</th></tr></thead>
                <tbody>{body_rows if body_rows else '<tr><td colspan="6">Chưa có lịch hẹn nào.</td></tr>'}</tbody>
            </table>
        </div>
        """
        self.send_html(layout("Lịch hẹn", content, user, "appointments", self.query_msg()))

    def appointment_detail(self, appointment_id):
        user = self.require_user()
        if not user:
            return
        if not str(appointment_id).isdigit():
            return self.redirect("/appointments?msg=" + quote("Mã lịch hẹn không hợp lệ."))

        with db() as conn:
            cursor = conn.execute(
                """
                SELECT a.id, a.customer_id, a.pet_name, a.pet_type, a.appointment_date,
                       a.appointment_time, a.status, a.estimated_total, a.note,
                       u.full_name, u.email, u.phone
                FROM appointments a
                JOIN users u ON u.id = a.customer_id
                WHERE a.id = ?
                """,
                (appointment_id,),
            )
            appt = cursor.fetchone()
            if not appt:
                return self.redirect("/appointments?msg=" + quote("Không tìm thấy lịch hẹn."))
            if user["role"] == "customer" and appt[1] != user["id"]:
                return self.redirect("/appointments?msg=" + quote("Bạn không có quyền xem lịch hẹn này."))

            cursor = conn.execute(
                """
                SELECT s.name, ads.quantity, ads.unit_price, ads.quantity * ads.unit_price AS total
                FROM appointment_services ads
                JOIN services s ON s.id = ads.service_id
                WHERE ads.appointment_id = ?
                """,
                (appointment_id,),
            )
            details = cursor.fetchall()

        detail_rows = "".join(
            f"<tr><td>{escape(row[0])}</td><td>{row[1]}</td><td>{money(row[2])}</td><td>{money(row[3])}</td></tr>"
            for row in details
        )
        cancel_form = ""
        if user["role"] == "customer" and appt[6] == "booked":
            cancel_form = f"""
            <form method="post" action="/appointments/cancel">
                <input type="hidden" name="appointment_id" value="{appt[0]}">
                <button class="btn danger" type="submit">Hủy lịch hẹn</button>
            </form>
            """
        invoice_form = ""
        if user["role"] in ("staff", "manager") and appt[6] == "booked":
            invoice_form = f"""
            <form method="post" action="/invoices">
                <input type="hidden" name="appointment_id" value="{appt[0]}">
                <button class="btn success" type="submit">Tạo hóa đơn</button>
            </form>
            """
        content = f"""
        <div class="card">
            <h1>Chi tiết lịch hẹn #{appt[0]}</h1>
            <div class="grid grid-2">
                <p><strong>Khách hàng:</strong> {escape(appt[9])}<br><span class="muted">{escape(appt[11])} - {escape(appt[10])}</span></p>
                <p><strong>Thú cưng:</strong> {escape(appt[2])} - {escape(appt[3])}<br><strong>Trạng thái:</strong> {status_badge(appt[6])}</p>
                <p><strong>Thời gian:</strong> {appt[5]} ngày {appt[4]}</p>
                <p><strong>Ghi chú:</strong> {escape(appt[8] or 'Không có')}</p>
            </div>
            <table>
                <thead><tr><th>Dịch vụ</th><th>Số lượng</th><th>Đơn giá</th><th>Thành tiền</th></tr></thead>
                <tbody>{detail_rows}</tbody>
            </table>
            <p class="right"><strong>Tổng dự kiến: {money(appt[7])}</strong></p>
            <div class="actions">
                <a class="btn secondary" href="/appointments">Quay lại</a>
                {cancel_form}
                {invoice_form}
            </div>
        </div>
        """
        self.send_html(layout("Chi tiết lịch hẹn", content, user, "appointments"))
    
    def cancel_appointment(self):
        user = self.require_roles(("customer",))
        if not user:
            return
        form = self.read_form()
        appointment_id = form.get("appointment_id", ["0"])[0]
        
        with db() as conn:
            conn.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ? AND customer_id = ?", (appointment_id, user["id"]))
        
        self.redirect("/appointments?msg=" + quote("Đã hủy lịch hẹn."))
    
    def manage_services(self):
        user = self.require_roles(("manager",))
        if not user:
            return
        form = self.read_form()
        action = form.get("action", [""])[0]
        
        with db() as conn:
            if action == "add":
                name = form.get("name", [""])[0].strip()
                description = form.get("description", [""])[0].strip()
                price = form.get("price", ["0"])[0]
                
                conn.execute(
                    "INSERT INTO services(name, description, price) VALUES (?, ?, ?)",
                    (name, description, int(price)),
                )
                self.redirect("/services?msg=" + quote("Thêm dịch vụ thành công."))
            else:
                self.redirect("/services?msg=" + quote("Hành động không hợp lệ."))
    
    def create_invoice(self):
        user = self.require_roles(("staff", "manager"))
        if not user:
            return
        form = self.read_form()
        appointment_id = form.get("appointment_id", ["0"])[0]
        
        with db() as conn:
            cursor = conn.execute(
                "SELECT * FROM appointments WHERE id = ? AND status = 'booked'",
                (appointment_id,)
            )
            appt = cursor.fetchone()
            if not appt:
                return self.redirect("/invoices?msg=" + quote("Lịch hẹn không tồn tại."))
            
            appt_dict = {col[0]: appt[i] for i, col in enumerate(cursor.description)}
            
            cursor = conn.execute(
                """
                INSERT INTO invoices(appointment_id, staff_id, total_amount)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?)
                """,
                (appointment_id, user["id"], appt_dict["estimated_total"]),
            )
            invoice_id = cursor.fetchone()[0]
            
            cursor = conn.execute(
                """
                SELECT s.name, ads.quantity, ads.unit_price, ads.quantity * ads.unit_price AS total
                FROM appointment_services ads JOIN services s ON s.id = ads.service_id
                WHERE ads.appointment_id = ?
                """,
                (appointment_id,),
            )
            details = cursor.fetchall()
            
            for row in details:
                conn.execute(
                    """
                    INSERT INTO invoice_details(invoice_id, service_name, quantity, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (int(invoice_id), row[0], row[1], row[2], row[3]),
                )
            
            conn.execute("UPDATE appointments SET status = 'paid' WHERE id = ?", (appointment_id,))
        
        self.redirect("/invoices?msg=" + quote("Đã tạo hóa đơn và ghi nhận thanh toán."))
    
    def invoices(self):
        user = self.require_roles(("staff", "manager"))
        if not user:
            return
        
        with db() as conn:
            cursor = conn.execute(
                """
                SELECT i.id, i.appointment_id, i.total_amount, i.created_at, 
                       a.pet_name, a.appointment_date, u.full_name, s.full_name
                FROM invoices i
                JOIN appointments a ON a.id = i.appointment_id
                JOIN users u ON u.id = a.customer_id
                JOIN users s ON s.id = i.staff_id
                ORDER BY i.created_at DESC
                """
            )
            rows = cursor.fetchall()
        
        body_rows = "".join(
            f"""
            <tr>
                <td>HD{row[0]:03d}</td>
                <td>{escape(row[6])}<br><span class="muted">{escape(row[4])}</span></td>
                <td>{escape(row[7])}</td>
                <td>{escape(row[5])}</td>
                <td>{money(row[2])}</td>
                <td>{status_badge('paid')}</td>
            </tr>
            """
            for row in rows
        )
        
        content = f"""
        <div class="card">
            <h1>Hóa đơn</h1>
            <table>
                <thead><tr><th>Mã hóa đơn</th><th>Khách hàng</th><th>Nhân viên</th><th>Ngày hẹn</th><th>Tổng tiền</th><th>Trạng thái</th></tr></thead>
                <tbody>{body_rows if body_rows else '<tr><td colspan="6">Chưa có hóa đơn.</td></tr>'}</tbody>
            </table>
        </div>
        """
        self.send_html(layout("Hóa đơn", content, user, "invoices", self.query_msg()))
    
    def stats(self):
        user = self.require_roles(("manager",))
        if not user:
            return
        
        with db() as conn:
            cursor = conn.execute("SELECT COALESCE(SUM(total_amount), 0) FROM invoices")
            revenue = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM appointments")
            appt_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'")
            customer_count = cursor.fetchone()[0]
            
            cursor = conn.execute(
                """
                SELECT s.name, COALESCE(SUM(ads.quantity), 0) AS used_count
                FROM services s
                LEFT JOIN appointment_services ads ON ads.service_id = s.id
                GROUP BY s.id, s.name
                ORDER BY used_count DESC, s.name
                """
            )
            service_rows = cursor.fetchall()
        
        rows = "".join(f"<tr><td>{escape(row[0])}</td><td>{row[1]}</td></tr>" for row in service_rows)
        content = f"""
        <div class="grid grid-3">
            <div class="card stat"><span>Doanh thu</span><strong>{money(revenue)}</strong></div>
            <div class="card stat"><span>Lịch hẹn</span><strong>{appt_count}</strong></div>
            <div class="card stat"><span>Khách hàng</span><strong>{customer_count}</strong></div>
        </div>
        <div class="card" style="margin-top:18px">
            <h1>Thống kê dịch vụ sử dụng</h1>
            <table><thead><tr><th>Dịch vụ</th><th>Số lần được chọn</th></tr></thead><tbody>{rows}</tbody></table>
        </div>
        """
        self.send_html(layout("Thống kê", content, user, "stats"))
    
    def log_message(self, format, *args):
        pass

def run():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), PetCareHandler)
    print(f"PetCare web is running at http://{HOST}:{PORT}")
    print("Demo accounts: khach@example.com / nhanvien@example.com / quanly@example.com | password: 123456")
    server.serve_forever()

if __name__ == "__main__":
    run()
