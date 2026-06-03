# -*- coding: utf-8 -*-
"""
Services Module - Quản lý dịch vụ
"""
from urllib.parse import quote
from database import db
from modules.core.common import escape, layout, current_user, money


class ServicesModule:
    """Handles service-related operations"""

    @staticmethod
    def services_page(handler):
        """Display services list"""
        user = current_user(handler)
        if not user:
            return handler.redirect("/login?msg=" + quote("Vui lòng đăng nhập"))

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
        handler.send_html(layout("Dịch vụ", content, user, "services"))

    @staticmethod
    def manage_services(handler):
        """Process service management actions (add, etc.) - Manager only"""
        user = current_user(handler)
        if not user:
            return handler.redirect("/login?msg=" + quote("Vui lòng đăng nhập"))
        if user["role"] != "manager":
            handler.send_html(layout("Lỗi", "<p>Bạn không có quyền truy cập trang này.</p>", user))
            return

        form = handler.read_form()
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
                handler.redirect("/services?msg=" + quote("Thêm dịch vụ thành công."))
            else:
                handler.redirect("/services?msg=" + quote("Hành động không hợp lệ."))
