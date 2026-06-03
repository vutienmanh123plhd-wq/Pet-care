# -*- coding: utf-8 -*-
"""
Common utilities - Helper functions dùng chung toàn ứng dụng
"""
import html
from http import cookies
from urllib.parse import quote
from database import db


def escape(value):
    """HTML escape helper function"""
    return html.escape("" if value is None else str(value), quote=True)


def money(value):
    """Format money display"""
    return f"{int(value):,.0f}đ".replace(",", ".")


def status_label(status):
    """Get Vietnamese label for status"""
    return {
        "booked": "Đã đặt",
        "cancelled": "Đã hủy",
        "paid": "Đã thanh toán",
    }.get(status, status)


def status_badge(status):
    """Get HTML badge for status"""
    cls = {"booked": "booked", "cancelled": "cancelled", "paid": "paid"}.get(status, "booked")
    return f'<span class="badge {cls}">{escape(status_label(status))}</span>'


def current_user(handler):
    """Get current logged-in user from session"""
    SESSIONS = getattr(handler.server, 'SESSIONS', {})
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
    """Render page layout with navigation"""
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
            nav_items += [("Quản lý nhân viên", "/employees", "employees")]
        nav_items += [("Hồ sơ cá nhân", "/profile", "profile")]
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


def service_summary(conn, appointment_id):
    """Get service summary for appointment"""
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
