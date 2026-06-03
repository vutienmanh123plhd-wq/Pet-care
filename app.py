# -*- coding: utf-8 -*-
"""
PetCare - Hệ thống quản lý cửa hàng chăm sóc thú cưng
Entry point: HTTP server + routing. Toàn bộ business logic nằm trong modules/.

Module map:
  modules/auth/         -> AccountsModule, PermissionsModule
  modules/appointments/ -> AppointmentsModule, InvoicesModule
  modules/services.py   -> ServicesModule
  modules/stats.py      -> StatsModule
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import mimetypes

from config import HOST, PORT
from database import init_db

# --- Import tất cả module từ sub-packages ---
from modules.auth.accounts import AccountsModule
from modules.auth.permissions import PermissionsModule
from modules.appointments.appointments import AppointmentsModule
from modules.appointments.invoices import InvoicesModule
from modules.services import ServicesModule
from modules.stats import StatsModule
from modules.core.common import escape, layout, current_user

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"


class PetCareHandler(BaseHTTPRequestHandler):

    # ------------------------------------------------------------------ #
    #  GET routing                                                         #
    # ------------------------------------------------------------------ #
    def do_GET(self):
        path = urlparse(self.path).path

        # Static files
        if path.startswith("/static/"):
            return self.serve_static(path)

        # Public pages
        if path == "/":
            return self.home()
        if path == "/login":
            return AccountsModule.login_page(self)
        if path == "/register":
            return AccountsModule.register_page(self)
        if path == "/logout":
            return AccountsModule.logout(self)

        # Dashboard & dịch vụ
        if path == "/dashboard":
            return StatsModule.dashboard(self)
        if path == "/services":
            return ServicesModule.services_page(self)

        # Lịch hẹn
        if path == "/appointments/new":
            return AppointmentsModule.create_appointment_page(self)
        if path.startswith("/appointments/") and path != "/appointments/new":
            appointment_id = path.rsplit("/", 1)[-1]
            return AppointmentsModule.appointment_detail(self, appointment_id)
        if path == "/appointments":
            return AppointmentsModule.appointments_list(self)

        # Hóa đơn
        if path == "/invoices":
            return InvoicesModule.invoices_list(self)

        # Thống kê
        if path == "/stats":
            return StatsModule.stats_page(self)

        # Hồ sơ cá nhân
        if path == "/profile/edit":
            return AccountsModule.profile_edit_page(self)
        if path == "/profile":
            return AccountsModule.profile_page(self)

        # Quản lý nhân viên
        if path == "/employees/add":
            return PermissionsModule.add_employee_page(self)
        if path.startswith("/employees/") and path.endswith("/edit"):
            emp_id = path.split("/")[-2]
            return PermissionsModule.edit_employee_page(self, emp_id)
        if path.startswith("/employees/") and path.endswith("/delete"):
            emp_id = path.split("/")[-2]
            return PermissionsModule.delete_employee_page(self, emp_id)
        if path == "/employees":
            return PermissionsModule.employees_list(self)

        self.send_error(404)

    # ------------------------------------------------------------------ #
    #  POST routing                                                        #
    # ------------------------------------------------------------------ #
    def do_POST(self):
        path = self.path

        # Auth
        if path == "/login":
            return AccountsModule.login_action(self)
        if path == "/register":
            return AccountsModule.register_action(self)
        if path == "/profile/edit":
            return AccountsModule.profile_edit_action(self)

        # Lịch hẹn
        if path == "/appointments/new":
            return AppointmentsModule.create_appointment(self)
        if path == "/appointments/cancel":
            return AppointmentsModule.cancel_appointment(self)

        # Hóa đơn
        if path == "/invoices":
            return InvoicesModule.create_invoice(self)

        # Dịch vụ (quản lý bởi manager)
        if path == "/services/manage":
            return ServicesModule.manage_services(self)

        # Quản lý nhân viên
        if path == "/employees/add":
            return PermissionsModule.add_employee_action(self)
        if path.startswith("/employees/") and path.endswith("/edit"):
            emp_id = path.split("/")[-2]
            return PermissionsModule.edit_employee_action(self, emp_id)
        if path.startswith("/employees/") and path.endswith("/delete"):
            emp_id = path.split("/")[-2]
            return PermissionsModule.delete_employee_action(self, emp_id)

        self.send_error(404)

    # ------------------------------------------------------------------ #
    #  Trang chủ (public)                                                  #
    # ------------------------------------------------------------------ #
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


    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #
    def send_html(self, html_content):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def serve_static(self, path):
        from urllib.parse import unquote
        relative_path = unquote(path.removeprefix("/static/"))
        base_dir = STATIC_DIR.resolve()
        target = (base_dir / relative_path).resolve()

        if target != base_dir and base_dir not in target.parents:
            self.send_error(403)
            return
        if not target.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, path, cookie=None):
        self.send_response(302)
        self.send_header("Location", path)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def read_form(self):
        from urllib.parse import parse_qs
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        return parse_qs(body)

    def log_message(self, format, *args):
        pass  # Tắt log mặc định của BaseHTTPRequestHandler


# ------------------------------------------------------------------ #
#  Khởi tạo server + SESSIONS store                                   #
# ------------------------------------------------------------------ #
def run():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), PetCareHandler)
    server.SESSIONS = {}  # Session store chia sẻ qua handler.server.SESSIONS

    print(f"PetCare web is running at http://{HOST}:{PORT}")
    print("Demo accounts: khach@example.com / nhanvien@example.com / quanly@example.com | password: 123456")
    server.serve_forever()

if __name__ == "__main__":
    run()
