# -*- coding: utf-8 -*-
"""
Invoices Module - Invoice Management
"""
from urllib.parse import quote, urlparse, parse_qs
from database import db
from modules.core.common import escape, layout, current_user, status_badge, money


class InvoicesModule:
    """Handles invoice-related operations"""

    @staticmethod
    def require_staff(handler):
        """Check if user is staff or manager"""
        user = current_user(handler)
        if not user:
            handler.redirect("/login?msg=" + quote("Vui lòng đăng nhập"))
            return None
        if user["role"] not in ("staff", "manager"):
            handler.send_html(layout("Lỗi", "<p>Bạn không có quyền truy cập trang này.</p>", user))
            return None
        return user

    @staticmethod
    def invoices_list(handler):
        """Display invoices list"""
        user = InvoicesModule.require_staff(handler)
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

        parsed = urlparse(handler.path)
        flash = parse_qs(parsed.query).get("msg", [""])[0]

        content = f"""
        <div class="card">
            <h1>Hóa đơn</h1>
            <table>
                <thead><tr><th>Mã hóa đơn</th><th>Khách hàng</th><th>Nhân viên</th><th>Ngày hẹn</th><th>Tổng tiền</th><th>Trạng thái</th></tr></thead>
                <tbody>{body_rows if body_rows else '<tr><td colspan="6">Chưa có hóa đơn.</td></tr>'}</tbody>
            </table>
        </div>
        """
        handler.send_html(layout("Hóa đơn", content, user, "invoices", flash))

    @staticmethod
    def create_invoice(handler):
        """Process create invoice"""
        user = InvoicesModule.require_staff(handler)
        if not user:
            return
        form = handler.read_form()
        appointment_id = form.get("appointment_id", ["0"])[0]

        with db() as conn:
            cursor = conn.execute(
                "SELECT * FROM appointments WHERE id = ? AND status = 'booked'",
                (appointment_id,)
            )
            appt = cursor.fetchone()
            if not appt:
                return handler.redirect("/invoices?msg=" + quote("Lịch hẹn không tồn tại."))

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

        handler.redirect("/invoices?msg=" + quote("Đã tạo hóa đơn và ghi nhận thanh toán."))
