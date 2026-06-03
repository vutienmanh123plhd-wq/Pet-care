# -*- coding: utf-8 -*-
"""
Appointments Module - Appointment Management
"""
from urllib.parse import quote, urlparse, parse_qs
from database import db
from modules.core.common import escape, layout, current_user, status_badge, money


class AppointmentsModule:
    """Handles appointment-related operations"""

    @staticmethod
    def require_user(handler):
        """Check if user is authenticated"""
        user = current_user(handler)
        if not user:
            handler.redirect("/login?msg=" + quote("Vui lòng đăng nhập"))
            return None
        return user

    @staticmethod
    def require_roles(handler, roles):
        """Check if user has required roles"""
        user = AppointmentsModule.require_user(handler)
        if user and user["role"] not in roles:
            handler.send_html(layout("Lỗi", "<p>Bạn không có quyền truy cập trang này.</p>", user))
            return None
        return user

    @staticmethod
    def create_appointment_page(handler):
        """Display create appointment form"""
        user = AppointmentsModule.require_roles(handler, ("customer",))
        if not user:
            return

        with db() as conn:
            cursor = conn.execute("SELECT id, name, price FROM services WHERE status = 'active' ORDER BY name")
            services = cursor.fetchall()

        service_options = "".join(
            f'<label class="service-option"><input type="checkbox" name="service_id" value="{s[0]}"> {escape(s[1])} - {money(s[2])}</label>'
            for s in services
        )

        parsed = urlparse(handler.path)
        flash = parse_qs(parsed.query).get("msg", [""])[0]

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
        handler.send_html(layout("Đặt lịch", content, user, "book", flash))

    @staticmethod
    def create_appointment(handler):
        """Process create appointment"""
        user = AppointmentsModule.require_roles(handler, ("customer",))
        if not user:
            return
        form = handler.read_form()
        service_ids = [int(x) for x in form.get("service_id", []) if x.isdigit()]
        pet_name = form.get("pet_name", [""])[0].strip()
        pet_type = form.get("pet_type", [""])[0].strip()
        date = form.get("appointment_date", [""])[0]
        time = form.get("appointment_time", [""])[0]
        note = form.get("note", [""])[0].strip()

        if not service_ids:
            return handler.redirect("/appointments/new?msg=" + quote("Vui lòng chọn ít nhất một dịch vụ."))

        with db() as conn:
            placeholders = ",".join("?" * len(service_ids))
            cursor = conn.execute(f"SELECT * FROM services WHERE id IN ({placeholders}) AND status = 'active'", service_ids)
            rows = cursor.fetchall()

            if len(rows) != len(service_ids):
                return handler.redirect("/appointments/new?msg=" + quote("Dịch vụ không hợp lệ."))

            total = sum(row[3] for row in rows)
            ma_kh_row = conn.execute("SELECT MaKH FROM KhachHang WHERE MaNguoiDung = ?", (user["id"],)).fetchone()
            if not ma_kh_row:
                return handler.redirect("/appointments/new?msg=" + quote("Không tìm thấy thông tin khách hàng."))
            ma_kh = ma_kh_row[0]

            cursor = conn.execute(
                """
                INSERT INTO appointments(customer_id, pet_name, pet_type, appointment_date,
                                         appointment_time, estimated_total, note)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ma_kh, pet_name, pet_type, date, time, total, note),
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

        handler.redirect("/appointments?msg=" + quote("Đặt lịch hẹn thành công."))

    @staticmethod
    def appointments_list(handler):
        """Display appointments list"""
        user = AppointmentsModule.require_user(handler)
        if not user:
            return

        with db() as conn:
            if user["role"] == "customer":
                cursor = conn.execute(
                    """
                    SELECT a.id, a.pet_name, a.pet_type, a.appointment_date, a.appointment_time,
                           a.status, a.estimated_total
                    FROM appointments a
                    JOIN KhachHang kh ON kh.MaKH = a.customer_id
                    WHERE kh.MaNguoiDung = ?
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

        parsed = urlparse(handler.path)
        flash = parse_qs(parsed.query).get("msg", [""])[0]

        content = f"""
        <div class="card">
            <h1>Lịch hẹn</h1>
            <table>
                <thead><tr><th>Mã</th><th>Thú cưng</th><th>Ngày giờ</th><th>Tổng tiền</th><th>Trạng thái</th><th>Hành động</th></tr></thead>
                <tbody>{body_rows if body_rows else '<tr><td colspan="6">Chưa có lịch hẹn nào.</td></tr>'}</tbody>
            </table>
        </div>
        """
        handler.send_html(layout("Lịch hẹn", content, user, "appointments", flash))

    @staticmethod
    def appointment_detail(handler, appointment_id):
        """Display appointment details"""
        user = AppointmentsModule.require_user(handler)
        if not user:
            return
        if not str(appointment_id).isdigit():
            return handler.redirect("/appointments?msg=" + quote("Mã lịch hẹn không hợp lệ."))

        with db() as conn:
            cursor = conn.execute(
                """
                SELECT a.id, kh.MaNguoiDung, a.pet_name, a.pet_type, a.appointment_date,
                       a.appointment_time, a.status, a.estimated_total, a.note,
                       nd.HoTen, nd.Email, nd.SDT
                FROM appointments a
                JOIN KhachHang kh ON kh.MaKH = a.customer_id
                JOIN NguoiDung nd ON nd.MaNguoiDung = kh.MaNguoiDung
                WHERE a.id = ?
                """,
                (appointment_id,),
            )
            appt = cursor.fetchone()
            if not appt:
                return handler.redirect("/appointments?msg=" + quote("Không tìm thấy lịch hẹn."))
            if user["role"] == "customer" and appt[1] != user["id"]:
                return handler.redirect("/appointments?msg=" + quote("Bạn không có quyền xem lịch hẹn này."))

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
        handler.send_html(layout("Chi tiết lịch hẹn", content, user, "appointments"))

    @staticmethod
    def cancel_appointment(handler):
        """Process cancel appointment"""
        user = AppointmentsModule.require_roles(handler, ("customer",))
        if not user:
            return
        form = handler.read_form()
        appointment_id = form.get("appointment_id", ["0"])[0]

        with db() as conn:
            conn.execute(
                """
                UPDATE appointments SET status = 'cancelled' 
                WHERE id = ? AND customer_id = (SELECT MaKH FROM KhachHang WHERE MaNguoiDung = ?)
                """,
                (appointment_id, user["id"])
            )

        handler.redirect("/appointments?msg=" + quote("Đã hủy lịch hẹn."))
