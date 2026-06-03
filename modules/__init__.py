# -*- coding: utf-8 -*-
"""
PetCare Modules Package

Sub-packages:
  - core/         : Helper functions dùng chung (escape, layout, money...)
  - auth/         : Tài khoản & Phân quyền (AccountsModule, PermissionsModule)
  - appointments/ : Quản lý lịch hẹn & Hóa đơn (AppointmentsModule, InvoicesModule)
  - services/     : Quản lý dịch vụ (ServicesModule)
  - stats/        : Thống kê & Dashboard (StatsModule)
"""
from .core.common import escape, layout, current_user, money, status_badge, service_summary
from .auth import AccountsModule, PermissionsModule
from .appointments import AppointmentsModule, InvoicesModule
from .services import ServicesModule
from .stats import StatsModule

__all__ = [
    # Helpers
    "escape", "layout", "current_user", "money", "status_badge", "service_summary",
    # Modules
    "AccountsModule", "PermissionsModule",
    "AppointmentsModule", "InvoicesModule",
    "ServicesModule",
    "StatsModule",
]

