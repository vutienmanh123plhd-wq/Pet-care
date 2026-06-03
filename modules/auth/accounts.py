# -*- coding: utf-8 -*-
"""
Accounts Module - Login, Register, Profile Management
"""
from urllib.parse import quote, urlparse, parse_qs
import secrets
from database import db, password_hash
from modules.core.common import escape, layout, current_user


class AccountsModule:
    """Handles account-related operations"""

    @staticmethod
    def login_page(handler):
        """Display login form"""
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
        parsed = urlparse(handler.path)
        flash = parse_qs(parsed.query).get("msg", [""])[0]
        handler.send_html(layout("Đăng nhập", content, flash=flash))

    @staticmethod
    def login_action(handler):
        """Process login"""
        form = handler.read_form()
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
            return handler.redirect("/login?msg=" + quote("Email hoặc mật khẩu không đúng."))

        sid = secrets.token_urlsafe(32)
        SESSIONS = getattr(handler.server, 'SESSIONS', {})
        SESSIONS[sid] = user["id"]
        handler.server.SESSIONS = SESSIONS
        handler.redirect("/dashboard", f"sid={sid}; Path=/; HttpOnly; SameSite=Lax")

    @staticmethod
    def register_page(handler):
        """Display registration form"""
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
        parsed = urlparse(handler.path)
        flash = parse_qs(parsed.query).get("msg", [""])[0]
        handler.send_html(layout("Đăng ký", content, flash=flash))

    @staticmethod
    def register_action(handler):
        """Process registration"""
        form = handler.read_form()
        full_name = form.get("full_name", [""])[0].strip()
        email = form.get("email", [""])[0].strip().lower()
        phone = form.get("phone", [""])[0].strip()
        address = form.get("address", [""])[0].strip()
        password = form.get("password", [""])[0]
        confirm = form.get("confirm", [""])[0]

        if not all([full_name, email, phone, address, password]):
            return handler.redirect("/register?msg=" + quote("Vui lòng điền tất cả thông tin."))
        if password != confirm:
            return handler.redirect("/register?msg=" + quote("Mật khẩu không khớp."))

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
                return handler.redirect("/register?msg=" + quote("Email đã được sử dụng."))

        handler.redirect("/login?msg=" + quote("Đăng ký thành công. Vui lòng đăng nhập."))

    @staticmethod
    def profile_page(handler):
        """Display user profile"""
        user = current_user(handler)
        if not user:
            return handler.redirect("/login?msg=" + quote("Vui lòng đăng nhập"))

        role_map = {"customer": "Khách hàng", "staff": "Nhân viên", "manager": "Quản lý"}
        role_label = role_map.get(user["role"], user["role"])

        content = f"""
        <div class="hero">
            <h1>Hồ sơ cá nhân</h1>
        </div>
        <div class="card">
            <div class="grid grid-2">
                <p><strong>Họ tên:</strong> {escape(user['full_name'])}</p>
                <p><strong>Email:</strong> {escape(user['email'])}</p>
                <p><strong>Điện thoại:</strong> {escape(user['phone'] or 'Chưa cập nhật')}</p>
                <p><strong>Địa chỉ:</strong> {escape(user['address'] or 'Chưa cập nhật')}</p>
                <p><strong>Vai trò:</strong> {escape(role_label)}</p>
                <p><strong>Trạng thái:</strong> {escape(user['status'])}</p>
            </div>
            <div class="actions">
                <a class="btn" href="/profile/edit">Cập nhật hồ sơ</a>
                <a class="btn secondary" href="/dashboard">Quay lại</a>
            </div>
        </div>
        """
        handler.send_html(layout("Hồ sơ cá nhân", content, user, "profile"))

    @staticmethod
    def profile_edit_page(handler):
        """Display profile edit form"""
        user = current_user(handler)
        if not user:
            return handler.redirect("/login?msg=" + quote("Vui lòng đăng nhập"))

        parsed = urlparse(handler.path)
        flash = parse_qs(parsed.query).get("msg", [""])[0]

        content = f"""
        <div class="hero">
            <h1>Cập nhật hồ sơ cá nhân</h1>
        </div>
        <div class="card">
            <form method="post" action="/profile/edit">
                <div class="form-row">
                    <div><label>Họ tên</label><input name="full_name" type="text" value="{escape(user['full_name'])}" required></div>
                    <div><label>Email</label><input name="email" type="email" value="{escape(user['email'])}" required></div>
                </div>
                <div class="form-row">
                    <div><label>Điện thoại</label><input name="phone" type="tel" value="{escape(user['phone'] or '')}" required></div>
                    <div><label>Địa chỉ</label><input name="address" type="text" value="{escape(user['address'] or '')}" required></div>
                </div>
                <label>Đổi mật khẩu (để trống nếu không muốn đổi)</label>
                <div class="form-row">
                    <div><label>Mật khẩu mới</label><input name="new_password" type="password" placeholder="Để trống nếu không đổi"></div>
                    <div><label>Xác nhận mật khẩu</label><input name="confirm_password" type="password" placeholder="Để trống nếu không đổi"></div>
                </div>
                <div class="actions">
                    <button class="btn" type="submit">Lưu thay đổi</button>
                    <a class="btn secondary" href="/profile">Hủy</a>
                </div>
            </form>
        </div>
        """
        handler.send_html(layout("Cập nhật hồ sơ", content, user, "profile", flash))

    @staticmethod
    def profile_edit_action(handler):
        """Process profile update"""
        user = current_user(handler)
        if not user:
            return handler.redirect("/login?msg=" + quote("Vui lòng đăng nhập"))

        form = handler.read_form()
        full_name = form.get("full_name", [""])[0].strip()
        email = form.get("email", [""])[0].strip().lower()
        phone = form.get("phone", [""])[0].strip()
        address = form.get("address", [""])[0].strip()
        new_password = form.get("new_password", [""])[0]
        confirm_password = form.get("confirm_password", [""])[0]

        if not all([full_name, email, phone, address]):
            return handler.redirect("/profile/edit?msg=" + quote("Vui lòng điền tất cả thông tin bắt buộc."))

        if new_password and new_password != confirm_password:
            return handler.redirect("/profile/edit?msg=" + quote("Mật khẩu không khớp."))

        with db() as conn:
            try:
                if new_password:
                    conn.execute(
                        """
                        UPDATE users SET full_name = ?, email = ?, phone = ?, address = ?, password_hash = ?
                        WHERE id = ?
                        """,
                        (full_name, email, phone, address, password_hash(new_password), user["id"]),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE users SET full_name = ?, email = ?, phone = ?, address = ?
                        WHERE id = ?
                        """,
                        (full_name, email, phone, address, user["id"]),
                    )
            except Exception:
                return handler.redirect("/profile/edit?msg=" + quote("Email đã được sử dụng bởi tài khoản khác."))

        handler.redirect("/profile?msg=" + quote("Cập nhật hồ sơ thành công."))

    @staticmethod
    def logout(handler):
        """Process logout"""
        SESSIONS = getattr(handler.server, 'SESSIONS', {})
        from http import cookies
        jar = cookies.SimpleCookie(handler.headers.get("Cookie", ""))
        sid = jar.get("sid")
        if sid:
            SESSIONS.pop(sid.value, None)
        expired_cookie = "sid=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        handler.redirect("/login?msg=" + quote("Đăng xuất thành công."), expired_cookie)
