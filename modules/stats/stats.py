# -*- coding: utf-8 -*-
"""
Stats Module - Thống kê & Dashboard
"""
from urllib.parse import quote
from database import db
from modules.core.common import escape, layout, current_user, money


class StatsModule:
    """Handles statistics and dashboard operations"""

    @staticmethod
    def dashboard(handler):
        """Display user dashboard"""
        user = current_user(handler)
        if not user:
            return handler.redirect("/login?msg=" + quote("Vui lòng đăng nhập"))

        content = f"""
        <div class="hero">
            <h1>Xin chào, {escape(user['full_name'])}</h1>
            <p class="muted">Chào mừng bạn đến với hệ thống quản lý cửa hàng chăm sóc thú cưng.</p>
        </div>
        """
        handler.send_html(layout("Tổng quan", content, user, "dashboard"))

    @staticmethod
    def stats_page(handler):
        """Display statistics - Manager only"""
        user = current_user(handler)
        if not user:
            return handler.redirect("/login?msg=" + quote("Vui lòng đăng nhập"))
        if user["role"] != "manager":
            handler.send_html(layout("Lỗi", "<p>Bạn không có quyền truy cập trang này.</p>", user))
            return

        with db() as conn:
            cursor = conn.execute("SELECT COALESCE(SUM(total_amount), 0) FROM invoices")
            revenue = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM appointments")
            appt_count = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM KhachHang")
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

        rows = "".join(
            f"<tr><td>{escape(row[0])}</td><td>{row[1]}</td></tr>"
            for row in service_rows
        )
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
        handler.send_html(layout("Thống kê", content, user, "stats"))
