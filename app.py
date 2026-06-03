# -*- coding: utf-8 -*-
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse
import hashlib
import html
import mimetypes
import secrets
import sqlite3


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "petcare.db"
SCHEMA_PATH = ROOT / "schema.sql"
STATIC_DIR = ROOT / "static"
HOST = "127.0.0.1"
PORT = 8000
SESSIONS = {}


def escape(value):
    return html.escape("" if value is None else str(value), quote=True)


def password_hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    with db() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count:
            return
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
        conn.execute(
            """
            INSERT INTO appointments(customer_id, pet_name, pet_type, appointment_date,
                                     appointment_time, status, estimated_total, note)
            VALUES (1, 'Milo', 'Chó Poodle', '2026-06-10', '09:00', 'booked', 450000,
                    'Tắm và mát xa nhẹ')
            """
        )
        conn.execute(
            """
            INSERT INTO appointment_services(appointment_id, service_id, quantity, unit_price)
            VALUES (1, 1, 1, 200000), (1, 2, 1, 250000)
            """
        )


def money(value):
    text = f"{float(value or 0):,.0f}".replace(",", ".")
    return f"{text} VND"


def role_label(role):
    return {
        "customer": "Khách hàng",
        "staff": "Nhân viên",
        "manager": "Quản lý",
    }.get(role, role)


def status_label(status):
    return {
        "booked": "Đã đặt",
        "cancelled": "Đã hủy",
        "paid": "Đã thanh toán",
    }.get(status, status)


def status_badge(status):
    cls = {"booked": "booked", "cancelled": "cancelled", "paid": "paid"}.get(status, "booked")
    return f'<span class="badge {cls}">{escape(status_label(status))}</span>'


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
    return ", ".join(f"{row['name']} x{row['quantity']}" for row in rows)


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
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


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
        user_pill = f'<div class="user-pill">{escape(user["full_name"])} - {role_label(user["role"])}</div>'
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


class PetCareHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.address_string(), fmt % args))

    def send_html(self, html_text, status=200, cookie_header=None):
        data = html_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        if cookie_header:
            self.send_header("Set-Cookie", cookie_header)
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, target, cookie_header=None):
        self.send_response(303)
        self.send_header("Location", target)
        if cookie_header:
            self.send_header("Set-Cookie", cookie_header)
        self.end_headers()

    def read_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return parse_qs(raw, keep_blank_values=True)

    def require_user(self):
        user = current_user(self)
        if not user:
            self.redirect("/login?msg=" + quote("Vui lòng đăng nhập trước."))
            return None
        return user

    def require_roles(self, roles):
        user = self.require_user()
        if not user:
            return None
        if user["role"] not in roles:
            self.redirect("/dashboard?msg=" + quote("Bạn không có quyền truy cập chức năng này."))
            return None
        return user

    def query_msg(self):
        parsed = urlparse(self.path)
        return parse_qs(parsed.query).get("msg", [""])[0]

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/static/"):
            return self.serve_static(path)
        routes = {
            "/": self.home,
            "/login": self.login_page,
            "/register": self.register_page,
            "/logout": self.logout,
            "/dashboard": self.dashboard,
            "/services": self.services,
            "/appointments": self.appointments,
            "/appointments/new": self.new_appointment,
            "/appointment": self.appointment_detail,
            "/invoices": self.invoices,
            "/stats": self.stats,
        }
        handler = routes.get(path)
        if handler:
            return handler()
        self.send_html(layout("Không tìm thấy", "<div class='card'><h1>404</h1><p>Không tìm thấy trang.</p></div>"), 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        routes = {
            "/login": self.login_action,
            "/register": self.register_action,
            "/appointments/new": self.create_appointment,
            "/appointments/cancel": self.cancel_appointment,
            "/invoices/create": self.create_invoice,
            "/services/create": self.create_service,
            "/services/toggle": self.toggle_service,
        }
        handler = routes.get(parsed.path)
        if handler:
            return handler()
        self.redirect("/dashboard?msg=" + quote("Yêu cầu không hợp lệ."))

    def serve_static(self, path):
        rel = unquote(path.replace("/static/", "", 1))
        file_path = STATIC_DIR / rel
        if not file_path.exists() or not file_path.is_file():
            self.send_response(404)
            self.end_headers()
            return
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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
            user = conn.execute("SELECT * FROM users WHERE email = ? AND status = 'active'", (email,)).fetchone()
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
                    <div><label>Họ tên</label><input name="full_name" required></div>
                    <div><label>Email</label><input name="email" type="email" required></div>
                </div>
                <div class="form-row">
                    <div><label>Số điện thoại</label><input name="phone"></div>
                    <div><label>Mật khẩu</label><input name="password" type="password" required></div>
                </div>
                <label>Địa chỉ</label><input name="address">
                <div class="actions"><button class="btn" type="submit">Tạo tài khoản</button></div>
            </form>
        </div>
        """
        self.send_html(layout("Đăng ký", content, flash=self.query_msg()))

    def register_action(self):
        form = self.read_form()
        values = {
            "full_name": form.get("full_name", [""])[0].strip(),
            "email": form.get("email", [""])[0].strip().lower(),
            "phone": form.get("phone", [""])[0].strip(),
            "address": form.get("address", [""])[0].strip(),
            "password": form.get("password", [""])[0],
        }
        if not values["full_name"] or not values["email"] or not values["password"]:
            return self.redirect("/register?msg=" + quote("Vui lòng nhập đầy đủ thông tin bắt buộc."))
        try:
            with db() as conn:
                conn.execute(
                    """
                    INSERT INTO users(full_name, email, phone, address, role, password_hash)
                    VALUES (?, ?, ?, ?, 'customer', ?)
                    """,
                    (values["full_name"], values["email"], values["phone"], values["address"], password_hash(values["password"])),
                )
        except sqlite3.IntegrityError:
            return self.redirect("/register?msg=" + quote("Email đã tồn tại."))
        self.redirect("/login?msg=" + quote("Đăng ký thành công, vui lòng đăng nhập."))

    def logout(self):
        raw_cookie = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie(raw_cookie)
        sid = jar.get("sid")
        if sid:
            SESSIONS.pop(sid.value, None)
        self.redirect("/", "sid=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")

    def dashboard(self):
        user = self.require_user()
        if not user:
            return
        with db() as conn:
            appointments = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
            services = conn.execute("SELECT COUNT(*) FROM services WHERE status = 'active'").fetchone()[0]
            invoices = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
            revenue = conn.execute("SELECT COALESCE(SUM(total_amount), 0) FROM invoices").fetchone()[0]
        quick = []
        if user["role"] == "customer":
            quick = [("/appointments/new", "Đặt lịch hẹn"), ("/appointments", "Xem lịch của tôi")]
        elif user["role"] == "staff":
            quick = [("/appointments", "Kiểm tra lịch hẹn"), ("/invoices", "Xem hóa đơn")]
        else:
            quick = [("/services", "Quản lý dịch vụ"), ("/stats", "Xem thống kê")]
        quick_html = "".join(f'<a class="btn" href="{href}">{label}</a>' for href, label in quick)
        content = f"""
        <div class="grid grid-3">
            <div class="card stat"><span>Tổng lịch hẹn</span><strong>{appointments}</strong></div>
            <div class="card stat"><span>Dịch vụ đang cung cấp</span><strong>{services}</strong></div>
            <div class="card stat"><span>Hóa đơn</span><strong>{invoices}</strong></div>
        </div>
        <div class="card" style="margin-top:18px">
            <h1>Xin chào, {escape(user['full_name'])}</h1>
            <p class="muted">Vai trò hiện tại: {role_label(user['role'])}. Doanh thu đã ghi nhận: <strong>{money(revenue)}</strong>.</p>
            <div class="actions">{quick_html}</div>
        </div>
        """
        self.send_html(layout("Tổng quan", content, user, "dashboard", self.query_msg()))

    def services(self):
        user = self.require_user()
        if not user:
            return
        with db() as conn:
            rows = conn.execute("SELECT * FROM services ORDER BY id DESC").fetchall()
        table_rows = []
        for row in rows:
            action = ""
            if user["role"] == "manager":
                label = "Tạm ngừng" if row["status"] == "active" else "Mở lại"
                action = f"""
                <form method="post" action="/services/toggle">
                    <input type="hidden" name="id" value="{row['id']}">
                    <button class="btn secondary" type="submit">{label}</button>
                </form>
                """
            table_rows.append(
                f"""
                <tr>
                    <td>{escape(row['name'])}</td>
                    <td>{escape(row['description'])}</td>
                    <td>{money(row['price'])}</td>
                    <td>{'Đang cung cấp' if row['status'] == 'active' else 'Tạm ngừng'}</td>
                    <td>{action}</td>
                </tr>
                """
            )
        create_form = ""
        if user["role"] == "manager":
            create_form = """
            <div class="card" style="margin-top:18px">
                <h2>Thêm dịch vụ</h2>
                <form method="post" action="/services/create">
                    <div class="form-row">
                        <div><label>Tên dịch vụ</label><input name="name" required></div>
                        <div><label>Đơn giá</label><input name="price" type="number" min="0" required></div>
                    </div>
                    <label>Mô tả</label><textarea name="description"></textarea>
                    <div class="actions"><button class="btn" type="submit">Lưu dịch vụ</button></div>
                </form>
            </div>
            """
        content = f"""
        <div class="card">
            <h1>Danh mục dịch vụ chăm sóc thú cưng</h1>
            <table>
                <thead><tr><th>Tên dịch vụ</th><th>Mô tả</th><th>Đơn giá</th><th>Trạng thái</th><th>Thao tác</th></tr></thead>
                <tbody>{''.join(table_rows)}</tbody>
            </table>
        </div>
        {create_form}
        """
        self.send_html(layout("Dịch vụ", content, user, "services", self.query_msg()))

    def create_service(self):
        user = self.require_roles(("manager",))
        if not user:
            return
        form = self.read_form()
        name = form.get("name", [""])[0].strip()
        description = form.get("description", [""])[0].strip()
        price = float(form.get("price", ["0"])[0] or 0)
        if not name:
            return self.redirect("/services?msg=" + quote("Tên dịch vụ không được để trống."))
        with db() as conn:
            conn.execute("INSERT INTO services(name, description, price) VALUES (?, ?, ?)", (name, description, price))
        self.redirect("/services?msg=" + quote("Đã thêm dịch vụ mới."))

    def toggle_service(self):
        user = self.require_roles(("manager",))
        if not user:
            return
        service_id = self.read_form().get("id", ["0"])[0]
        with db() as conn:
            row = conn.execute("SELECT status FROM services WHERE id = ?", (service_id,)).fetchone()
            if row:
                new_status = "inactive" if row["status"] == "active" else "active"
                conn.execute("UPDATE services SET status = ? WHERE id = ?", (new_status, service_id))
        self.redirect("/services?msg=" + quote("Đã cập nhật trạng thái dịch vụ."))

    def new_appointment(self):
        user = self.require_roles(("customer",))
        if not user:
            return
        with db() as conn:
            services = conn.execute("SELECT * FROM services WHERE status = 'active' ORDER BY name").fetchall()
        options = []
        for row in services:
            options.append(
                f"""
                <label class="service-option">
                    <input type="checkbox" name="service_id" value="{row['id']}">
                    <span><strong>{escape(row['name'])}</strong><br><span class="muted">{money(row['price'])}</span></span>
                </label>
                """
            )
        content = f"""
        <div class="card">
            <h1>Đặt lịch hẹn</h1>
            <form method="post" action="/appointments/new">
                <div class="form-row">
                    <div><label>Tên thú cưng</label><input name="pet_name" required placeholder="Milo"></div>
                    <div><label>Loại thú cưng</label><input name="pet_type" required placeholder="Chó Poodle"></div>
                </div>
                <div class="form-row">
                    <div><label>Ngày hẹn</label><input name="appointment_date" type="date" required></div>
                    <div><label>Giờ hẹn</label><input name="appointment_time" type="time" required></div>
                </div>
                <label>Chọn dịch vụ</label>
                <div class="service-list">{''.join(options)}</div>
                <label style="margin-top:16px">Ghi chú</label><textarea name="note" placeholder="Yêu cầu thêm nếu có"></textarea>
                <div class="actions"><button class="btn" type="submit">Xác nhận đặt lịch</button></div>
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
            placeholders = ",".join("?" for _ in service_ids)
            rows = conn.execute(f"SELECT * FROM services WHERE id IN ({placeholders}) AND status = 'active'", service_ids).fetchall()
            if len(rows) != len(service_ids):
                return self.redirect("/appointments/new?msg=" + quote("Dịch vụ không hợp lệ."))
            total = sum(row["price"] for row in rows)
            cur = conn.execute(
                """
                INSERT INTO appointments(customer_id, pet_name, pet_type, appointment_date,
                                         appointment_time, estimated_total, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user["id"], pet_name, pet_type, date, time, total, note),
            )
            appointment_id = cur.lastrowid
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO appointment_services(appointment_id, service_id, quantity, unit_price)
                    VALUES (?, ?, 1, ?)
                    """,
                    (appointment_id, row["id"], row["price"]),
                )
        self.redirect("/appointments?msg=" + quote("Đặt lịch hẹn thành công."))

    def appointments(self):
        user = self.require_user()
        if not user:
            return
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query).get("q", [""])[0].strip()
        where = []
        params = []
        if user["role"] == "customer":
            where.append("a.customer_id = ?")
            params.append(user["id"])
        elif q:
            where.append("(u.full_name LIKE ? OR u.phone LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        sql = """
            SELECT a.*, u.full_name, u.phone,
                   EXISTS(SELECT 1 FROM invoices i WHERE i.appointment_id = a.id) AS has_invoice
            FROM appointments a
            JOIN users u ON u.id = a.customer_id
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY a.appointment_date DESC, a.appointment_time DESC"
        with db() as conn:
            rows = conn.execute(sql, params).fetchall()
            body_rows = []
            for row in rows:
                services = service_summary(conn, row["id"])
                actions = [f'<a class="btn secondary" href="/appointment?id={row["id"]}">Chi tiết</a>']
                if user["role"] == "customer" and row["status"] == "booked":
                    actions.append(
                        f"""
                        <form method="post" action="/appointments/cancel">
                            <input type="hidden" name="id" value="{row['id']}">
                            <button class="btn danger" type="submit">Hủy</button>
                        </form>
                        """
                    )
                if user["role"] in ("staff", "manager") and row["status"] == "booked" and not row["has_invoice"]:
                    actions.append(
                        f"""
                        <form method="post" action="/invoices/create">
                            <input type="hidden" name="appointment_id" value="{row['id']}">
                            <button class="btn success" type="submit">Tạo hóa đơn</button>
                        </form>
                        """
                    )
                body_rows.append(
                    f"""
                    <tr>
                        <td>LH{row['id']:03d}</td>
                        <td>{escape(row['full_name'])}<br><span class="muted">{escape(row['phone'])}</span></td>
                        <td>{escape(row['pet_name'])}<br><span class="muted">{escape(row['pet_type'])}</span></td>
                        <td>{escape(row['appointment_date'])}<br>{escape(row['appointment_time'])}</td>
                        <td>{escape(services)}</td>
                        <td>{money(row['estimated_total'])}</td>
                        <td>{status_badge(row['status'])}</td>
                        <td><div class="actions">{''.join(actions)}</div></td>
                    </tr>
                    """
                )
        search_form = ""
        if user["role"] in ("staff", "manager"):
            search_form = f"""
            <form method="get" action="/appointments" class="card" style="margin-bottom:18px">
                <div class="form-row">
                    <div><label>Tìm khách hàng</label><input name="q" value="{escape(q)}" placeholder="Tên hoặc số điện thoại"></div>
                    <div class="actions" style="align-items:end"><button class="btn" type="submit">Tìm kiếm</button><a class="btn secondary" href="/appointments">Làm mới</a></div>
                </div>
            </form>
            """
        title = "Lịch hẹn của tôi" if user["role"] == "customer" else "Kiểm tra lịch hẹn khách hàng"
        content = f"""
        {search_form}
        <div class="card">
            <h1>{title}</h1>
            <table>
                <thead><tr><th>Mã</th><th>Khách hàng</th><th>Thú cưng</th><th>Thời gian</th><th>Dịch vụ</th><th>Giá dự kiến</th><th>Trạng thái</th><th>Thao tác</th></tr></thead>
                <tbody>{''.join(body_rows) if body_rows else '<tr><td colspan="8">Không có lịch hẹn phù hợp.</td></tr>'}</tbody>
            </table>
        </div>
        """
        self.send_html(layout("Lịch hẹn", content, user, "appointments", self.query_msg()))

    def appointment_detail(self):
        user = self.require_user()
        if not user:
            return
        appointment_id = parse_qs(urlparse(self.path).query).get("id", ["0"])[0]
        with db() as conn:
            appt = conn.execute(
                """
                SELECT a.*, u.full_name, u.email, u.phone
                FROM appointments a JOIN users u ON u.id = a.customer_id
                WHERE a.id = ?
                """,
                (appointment_id,),
            ).fetchone()
            if not appt:
                return self.redirect("/appointments?msg=" + quote("Không tìm thấy lịch hẹn."))
            if user["role"] == "customer" and appt["customer_id"] != user["id"]:
                return self.redirect("/appointments?msg=" + quote("Bạn không có quyền xem lịch hẹn này."))
            details = conn.execute(
                """
                SELECT s.name, ads.quantity, ads.unit_price, ads.quantity * ads.unit_price AS total
                FROM appointment_services ads
                JOIN services s ON s.id = ads.service_id
                WHERE ads.appointment_id = ?
                """,
                (appointment_id,),
            ).fetchall()
        detail_rows = "".join(
            f"<tr><td>{escape(row['name'])}</td><td>{row['quantity']}</td><td>{money(row['unit_price'])}</td><td>{money(row['total'])}</td></tr>"
            for row in details
        )
        content = f"""
        <div class="card">
            <h1>Chi tiết lịch hẹn LH{appt['id']:03d}</h1>
            <div class="grid grid-2">
                <p><strong>Khách hàng:</strong> {escape(appt['full_name'])}<br><span class="muted">{escape(appt['phone'])} - {escape(appt['email'])}</span></p>
                <p><strong>Thú cưng:</strong> {escape(appt['pet_name'])} - {escape(appt['pet_type'])}<br><strong>Trạng thái:</strong> {status_badge(appt['status'])}</p>
                <p><strong>Thời gian:</strong> {escape(appt['appointment_time'])} ngày {escape(appt['appointment_date'])}</p>
                <p><strong>Ghi chú:</strong> {escape(appt['note'] or 'Không có')}</p>
            </div>
            <table>
                <thead><tr><th>Dịch vụ</th><th>Số lượng</th><th>Đơn giá</th><th>Thành tiền</th></tr></thead>
                <tbody>{detail_rows}</tbody>
            </table>
            <p class="right"><strong>Tổng dự kiến: {money(appt['estimated_total'])}</strong></p>
            <div class="actions"><a class="btn secondary" href="/appointments">Quay lại</a></div>
        </div>
        """
        self.send_html(layout("Chi tiết lịch hẹn", content, user, "appointments"))

    def cancel_appointment(self):
        user = self.require_roles(("customer",))
        if not user:
            return
        appointment_id = self.read_form().get("id", ["0"])[0]
        with db() as conn:
            row = conn.execute("SELECT * FROM appointments WHERE id = ? AND customer_id = ?", (appointment_id, user["id"])).fetchone()
            if row and row["status"] == "booked":
                conn.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (appointment_id,))
                return self.redirect("/appointments?msg=" + quote("Đã hủy lịch hẹn."))
        self.redirect("/appointments?msg=" + quote("Không thể hủy lịch hẹn này."))

    def create_invoice(self):
        user = self.require_roles(("staff", "manager"))
        if not user:
            return
        appointment_id = self.read_form().get("appointment_id", ["0"])[0]
        with db() as conn:
            appt = conn.execute("SELECT * FROM appointments WHERE id = ? AND status = 'booked'", (appointment_id,)).fetchone()
            if not appt:
                return self.redirect("/appointments?msg=" + quote("Lịch hẹn không hợp lệ hoặc đã xử lý."))
            exists = conn.execute("SELECT id FROM invoices WHERE appointment_id = ?", (appointment_id,)).fetchone()
            if exists:
                return self.redirect("/appointments?msg=" + quote("Lịch hẹn đã có hóa đơn."))
            cur = conn.execute(
                "INSERT INTO invoices(appointment_id, staff_id, total_amount) VALUES (?, ?, ?)",
                (appointment_id, user["id"], appt["estimated_total"]),
            )
            invoice_id = cur.lastrowid
            details = conn.execute(
                """
                SELECT s.name, ads.quantity, ads.unit_price, ads.quantity * ads.unit_price AS total
                FROM appointment_services ads JOIN services s ON s.id = ads.service_id
                WHERE ads.appointment_id = ?
                """,
                (appointment_id,),
            ).fetchall()
            for row in details:
                conn.execute(
                    """
                    INSERT INTO invoice_details(invoice_id, service_name, quantity, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (invoice_id, row["name"], row["quantity"], row["unit_price"], row["total"]),
                )
            conn.execute("UPDATE appointments SET status = 'paid' WHERE id = ?", (appointment_id,))
        self.redirect("/invoices?msg=" + quote("Đã tạo hóa đơn và ghi nhận thanh toán."))

    def invoices(self):
        user = self.require_roles(("staff", "manager"))
        if not user:
            return
        with db() as conn:
            rows = conn.execute(
                """
                SELECT i.*, a.pet_name, a.appointment_date, u.full_name AS customer_name,
                       s.full_name AS staff_name
                FROM invoices i
                JOIN appointments a ON a.id = i.appointment_id
                JOIN users u ON u.id = a.customer_id
                JOIN users s ON s.id = i.staff_id
                ORDER BY i.created_at DESC
                """
            ).fetchall()
        body_rows = "".join(
            f"""
            <tr>
                <td>HD{row['id']:03d}</td>
                <td>{escape(row['customer_name'])}<br><span class="muted">{escape(row['pet_name'])}</span></td>
                <td>{escape(row['staff_name'])}</td>
                <td>{escape(row['appointment_date'])}</td>
                <td>{money(row['total_amount'])}</td>
                <td>{status_badge('paid')}</td>
            </tr>
            """
            for row in rows
        )
        content = f"""
        <div class="card">
            <h1>Danh sách hóa đơn</h1>
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
            revenue = conn.execute("SELECT COALESCE(SUM(total_amount), 0) FROM invoices").fetchone()[0]
            appt_count = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
            customer_count = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'").fetchone()[0]
            service_rows = conn.execute(
                """
                SELECT s.name, COALESCE(SUM(ads.quantity), 0) AS used_count
                FROM services s
                LEFT JOIN appointment_services ads ON ads.service_id = s.id
                GROUP BY s.id
                ORDER BY used_count DESC, s.name
                """
            ).fetchall()
        rows = "".join(f"<tr><td>{escape(row['name'])}</td><td>{row['used_count']}</td></tr>" for row in service_rows)
        content = f"""
        <div class="grid grid-3">
            <div class="card stat"><span>Doanh thu</span><strong>{money(revenue)}</strong></div>
            <div class="card stat"><span>Lịch hẹn</span><strong>{appt_count}</strong></div>
            <div class="card stat"><span>Khách hàng</span><strong>{customer_count}</strong></div>
        </div>
        <div class="card" style="margin-top:18px">
            <h1>Thống kê dịch vụ sử dụng</h1>
            <table><thead><tr><th>Dịch vụ</th><th>Số lượt được chọn</th></tr></thead><tbody>{rows}</tbody></table>
        </div>
        """
        self.send_html(layout("Thống kê", content, user, "stats"))


def run():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), PetCareHandler)
    print(f"PetCare web is running at http://{HOST}:{PORT}")
    print("Demo accounts: khach@example.com / nhanvien@example.com / quanly@example.com | password: 123456")
    server.serve_forever()


if __name__ == "__main__":
    run()
