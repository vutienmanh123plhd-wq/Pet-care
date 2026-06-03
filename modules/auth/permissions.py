# -*- coding: utf-8 -*-
"""
Permissions Module - Employee Management (Add, Edit, Delete)
"""
from urllib.parse import quote, urlparse, parse_qs
from database import db, password_hash
from modules.core.common import escape, layout, current_user


class PermissionsModule:
    """Handles employee/staff management and permissions"""

    @staticmethod
    def require_manager(handler):
        """Check if user is manager"""
        user = current_user(handler)
        if not user:
            handler.redirect("/login?msg=" + quote("Vui lòng đăng nhập"))
            return None
        if user["role"] != "manager":
            handler.send_html(layout("Lỗi", "<p>Bạn không có quyền truy cập trang này.</p>", user))
            return None
        return user

    @staticmethod
    def employees_list(handler):
        """Display list of employees"""
        user = PermissionsModule.require_manager(handler)
        if not user:
            return

        role_map = {"staff": "Nhân viên", "manager": "Quản lý"}

        with db() as conn:
            cursor = conn.execute(
                """
                SELECT id, full_name, email, phone, role, status, created_at
                FROM users
                WHERE role IN ('staff', 'manager')
                ORDER BY full_name
                """
            )
            rows = cursor.fetchall()

        body_rows = "".join(
            f"""
            <tr>
                <td>{escape(row[1])}</td>
                <td>{escape(row[2])}</td>
                <td>{escape(row[3] or '')}</td>
                <td>{escape(role_map.get(row[4], row[4]))}</td>
                <td>{escape(row[5])}</td>
                <td>
                    <a class="btn secondary" href="/employees/{row[0]}/edit">Sửa</a>
                    <a class="btn danger" href="/employees/{row[0]}/delete">Xóa</a>
                </td>
            </tr>
            """
            for row in rows
        )

        parsed = urlparse(handler.path)
        flash = parse_qs(parsed.query).get("msg", [""])[0]

        content = f"""
        <div class="card">
            <h1>Quản lý nhân viên</h1>
            <div class="actions">
                <a class="btn" href="/employees/add">Thêm nhân viên</a>
            </div>
            <table>
                <thead><tr><th>Họ tên</th><th>Email</th><th>Điện thoại</th><th>Vai trò</th><th>Trạng thái</th><th>Hành động</th></tr></thead>
                <tbody>{body_rows if body_rows else '<tr><td colspan="6">Chưa có nhân viên nào.</td></tr>'}</tbody>
            </table>
        </div>
        """
        handler.send_html(layout("Quản lý nhân viên", content, user, "employees", flash))

    @staticmethod
    def add_employee_page(handler):
        """Display add employee form"""
        user = PermissionsModule.require_manager(handler)
        if not user:
            return

        parsed = urlparse(handler.path)
        flash = parse_qs(parsed.query).get("msg", [""])[0]

        content = f"""
        <div class="hero">
            <h1>Thêm nhân viên</h1>
        </div>
        <div class="card">
            <form method="post" action="/employees/add">
                <div class="form-row">
                    <div><label>Họ tên</label><input name="full_name" type="text" required></div>
                    <div><label>Email</label><input name="email" type="email" required></div>
                </div>
                <div class="form-row">
                    <div><label>Điện thoại</label><input name="phone" type="tel" required></div>
                    <div><label>Địa chỉ</label><input name="address" type="text" required></div>
                </div>
                <div class="form-row">
                    <div>
                        <label>Vai trò</label>
                        <select name="role" required>
                            <option value="">-- Chọn vai trò --</option>
                            <option value="staff">Nhân viên</option>
                            <option value="manager">Quản lý</option>
                        </select>
                    </div>
                    <div><label>Mật khẩu</label><input name="password" type="password" value="123456" required></div>
                </div>
                <div class="actions">
                    <button class="btn" type="submit">Thêm nhân viên</button>
                    <a class="btn secondary" href="/employees">Hủy</a>
                </div>
            </form>
        </div>
        """
        handler.send_html(layout("Thêm nhân viên", content, user, "employees", flash))

    @staticmethod
    def add_employee_action(handler):
        """Process add employee"""
        user = PermissionsModule.require_manager(handler)
        if not user:
            return

        form = handler.read_form()
        full_name = form.get("full_name", [""])[0].strip()
        email = form.get("email", [""])[0].strip().lower()
        phone = form.get("phone", [""])[0].strip()
        address = form.get("address", [""])[0].strip()
        role = form.get("role", [""])[0].strip()
        password = form.get("password", ["123456"])[0]

        if not all([full_name, email, phone, address, role]):
            return handler.redirect("/employees/add?msg=" + quote("Vui lòng điền tất cả thông tin."))

        if role not in ("staff", "manager"):
            return handler.redirect("/employees/add?msg=" + quote("Vai trò không hợp lệ."))

        with db() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO users(full_name, email, phone, address, role, password_hash, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'active')
                    """,
                    (full_name, email, phone, address, role, password_hash(password)),
                )
            except Exception:
                return handler.redirect("/employees/add?msg=" + quote("Email đã được sử dụng."))

        handler.redirect("/employees?msg=" + quote("Thêm nhân viên thành công."))

    @staticmethod
    def edit_employee_page(handler, emp_id):
        """Display edit employee form"""
        user = PermissionsModule.require_manager(handler)
        if not user:
            return

        if not str(emp_id).isdigit():
            return handler.redirect("/employees?msg=" + quote("Mã nhân viên không hợp lệ."))

        with db() as conn:
            cursor = conn.execute(
                "SELECT id, full_name, email, phone, address, role, status FROM users WHERE id = ? AND role IN ('staff', 'manager')",
                (emp_id,)
            )
            emp = cursor.fetchone()
            if not emp:
                return handler.redirect("/employees?msg=" + quote("Không tìm thấy nhân viên."))

            emp_dict = {col[0]: emp[i] for i, col in enumerate(cursor.description)}

        role_staff_selected = "selected" if emp_dict["role"] == "staff" else ""
        role_manager_selected = "selected" if emp_dict["role"] == "manager" else ""
        status_active_selected = "selected" if emp_dict["status"] == "active" else ""
        status_inactive_selected = "selected" if emp_dict["status"] == "inactive" else ""

        parsed = urlparse(handler.path)
        flash = parse_qs(parsed.query).get("msg", [""])[0]

        content = f"""
        <div class="hero">
            <h1>Sửa thông tin nhân viên</h1>
        </div>
        <div class="card">
            <form method="post" action="/employees/{emp_id}/edit">
                <div class="form-row">
                    <div><label>Họ tên</label><input name="full_name" type="text" value="{escape(emp_dict['full_name'])}" required></div>
                    <div><label>Email</label><input name="email" type="email" value="{escape(emp_dict['email'])}" required></div>
                </div>
                <div class="form-row">
                    <div><label>Điện thoại</label><input name="phone" type="tel" value="{escape(emp_dict['phone'] or '')}" required></div>
                    <div><label>Địa chỉ</label><input name="address" type="text" value="{escape(emp_dict['address'] or '')}" required></div>
                </div>
                <div class="form-row">
                    <div>
                        <label>Vai trò</label>
                        <select name="role" required>
                            <option value="staff" {role_staff_selected}>Nhân viên</option>
                            <option value="manager" {role_manager_selected}>Quản lý</option>
                        </select>
                    </div>
                    <div>
                        <label>Trạng thái</label>
                        <select name="status" required>
                            <option value="active" {status_active_selected}>Hoạt động</option>
                            <option value="inactive" {status_inactive_selected}>Không hoạt động</option>
                        </select>
                    </div>
                </div>
                <label>Đổi mật khẩu (để trống nếu không muốn đổi)</label>
                <div class="form-row">
                    <div><label>Mật khẩu mới</label><input name="new_password" type="password" placeholder="Để trống nếu không đổi"></div>
                    <div><label>Xác nhận mật khẩu</label><input name="confirm_password" type="password" placeholder="Để trống nếu không đổi"></div>
                </div>
                <div class="actions">
                    <button class="btn" type="submit">Lưu thay đổi</button>
                    <a class="btn secondary" href="/employees">Hủy</a>
                </div>
            </form>
        </div>
        """
        handler.send_html(layout("Sửa nhân viên", content, user, "employees", flash))

    @staticmethod
    def edit_employee_action(handler, emp_id):
        """Process edit employee"""
        user = PermissionsModule.require_manager(handler)
        if not user:
            return

        form = handler.read_form()
        full_name = form.get("full_name", [""])[0].strip()
        email = form.get("email", [""])[0].strip().lower()
        phone = form.get("phone", [""])[0].strip()
        address = form.get("address", [""])[0].strip()
        role = form.get("role", [""])[0].strip()
        status = form.get("status", ["active"])[0].strip()
        new_password = form.get("new_password", [""])[0]
        confirm_password = form.get("confirm_password", [""])[0]

        if not all([full_name, email, phone, address, role]):
            return handler.redirect(f"/employees/{emp_id}/edit?msg=" + quote("Vui lòng điền tất cả thông tin bắt buộc."))

        if role not in ("staff", "manager"):
            return handler.redirect(f"/employees/{emp_id}/edit?msg=" + quote("Vai trò không hợp lệ."))

        if new_password and new_password != confirm_password:
            return handler.redirect(f"/employees/{emp_id}/edit?msg=" + quote("Mật khẩu không khớp."))

        with db() as conn:
            try:
                if new_password:
                    conn.execute(
                        """
                        UPDATE users SET full_name = ?, email = ?, phone = ?, address = ?, role = ?, status = ?, password_hash = ?
                        WHERE id = ?
                        """,
                        (full_name, email, phone, address, role, status, password_hash(new_password), emp_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE users SET full_name = ?, email = ?, phone = ?, address = ?, role = ?, status = ?
                        WHERE id = ?
                        """,
                        (full_name, email, phone, address, role, status, emp_id),
                    )
            except Exception:
                return handler.redirect(f"/employees/{emp_id}/edit?msg=" + quote("Email đã được sử dụng bởi tài khoản khác."))

        handler.redirect("/employees?msg=" + quote("Cập nhật thông tin nhân viên thành công."))

    @staticmethod
    def delete_employee_page(handler, emp_id):
        """Display delete employee confirmation"""
        user = PermissionsModule.require_manager(handler)
        if not user:
            return

        if not str(emp_id).isdigit():
            return handler.redirect("/employees?msg=" + quote("Mã nhân viên không hợp lệ."))

        if int(emp_id) == user["id"]:
            return handler.redirect("/employees?msg=" + quote("Không thể xóa tài khoản của chính bạn."))

        with db() as conn:
            cursor = conn.execute(
                "SELECT id, full_name, email, role FROM users WHERE id = ? AND role IN ('staff', 'manager')",
                (emp_id,)
            )
            emp = cursor.fetchone()
            if not emp:
                return handler.redirect("/employees?msg=" + quote("Không tìm thấy nhân viên."))

        role_map = {"staff": "Nhân viên", "manager": "Quản lý"}
        role_label = role_map.get(emp[3], emp[3])

        content = f"""
        <div class="hero">
            <h1>Xóa nhân viên</h1>
        </div>
        <div class="card">
            <p><strong>Bạn có chắc muốn xóa nhân viên này không?</strong></p>
            <p>Họ tên: {escape(emp[1])}<br>Email: {escape(emp[2])}<br>Vai trò: {escape(role_label)}</p>
            <form method="post" action="/employees/{emp_id}/delete">
                <div class="actions">
                    <button class="btn danger" type="submit">Xóa</button>
                    <a class="btn secondary" href="/employees">Hủy</a>
                </div>
            </form>
        </div>
        """
        handler.send_html(layout("Xóa nhân viên", content, user, "employees"))

    @staticmethod
    def delete_employee_action(handler, emp_id):
        """Process delete employee"""
        user = PermissionsModule.require_manager(handler)
        if not user:
            return

        if not str(emp_id).isdigit():
            return handler.redirect("/employees?msg=" + quote("Mã nhân viên không hợp lệ."))

        if int(emp_id) == user["id"]:
            return handler.redirect("/employees?msg=" + quote("Không thể xóa tài khoản của chính bạn."))

        with db() as conn:
            conn.execute("DELETE FROM users WHERE id = ? AND role IN ('staff', 'manager')", (emp_id,))

        handler.redirect("/employees?msg=" + quote("Xóa nhân viên thành công."))
