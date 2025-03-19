from typing import Tuple, Optional

from aiogram.types import InlineKeyboardMarkup, WebAppInfo, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models.sellers import UserRole

menu_structure = {
    "admins_main_menu": {
        "text": "📁 به پنل مدیریت خوش آمدید. لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        "row_width": [2, 2, 2, 1],
        "menu_type": "admin",
        "options": [
            {"text": "📊 داشبورد مدیریتی", "callback_data": "admin_dashboard"},
            {"text": "🤝 مدیریت عاملان فروش", "callback_data": "sellers"},
            {"text": "📡 مدیریت روترها", "callback_data": "admin_routers"},
            {"text": "📈 گزارش‌های سیستم", "callback_data": "system_reports"},
            {"text": "📨 ارسال پیام به فروشندگان", "callback_data": "send_message"},
            {"text": "🔍 جستجوی پیشرفته", "callback_data": "advanced_search"},
            {"text": "🖥️ کنترل سیستم", "callback_data": "system_control"},
        ],
    },
    # Router Management Menu
    "admin_routers": {
        "text": "📡 پنل مدیریت روترها",
        "row_width": [2, 2, 2, 1],
        "back": "admins_main_menu",
        "menu_type": "admin",
        "options": [
            {"text": "📊 وضعیت روترها", "callback_data": "router_status"},
            {"text": "➕ افزودن روتر جدید", "callback_data": "add_router"},
            {"text": "🔄 راه‌اندازی مجدد روتر", "callback_data": "restart_router"},
            {"text": "🔌 مدیریت برق روتر", "callback_data": "power_management"},
            {"text": "📈 مانیتورینگ ترافیک", "callback_data": "traffic_monitor"},
            {"text": "🔧 تنظیمات روتر", "callback_data": "router_settings"},
            {"text": "🚫 مسدود کردن IP", "callback_data": "block_ip"},
        ],
    },
    # Router Status Submenu
    "router_status": {
        "text": "📊 داشبورد وضعیت روترها",
        "row_width": [1, 1, 1, 1, 1],
        "back": "admin_routers",
        "menu_type": "admin",
        "options": [
            {"text": "🟢 روترهای فعال", "callback_data": "active_routers"},
            {"text": "🔴 روترهای غیرفعال", "callback_data": "inactive_routers"},
            {"text": "🔄 بروزرسانی وضعیت", "callback_data": "refresh_router_status"},
            {"text": "📊 گزارش وضعیت", "callback_data": "router_status_report"},
        ],
    },
    # Router Settings Submenu
    "router_settings": {
        "text": "🔧 تنظیمات پیکربندی روتر",
        "row_width": [2, 2, 1],
        "back": "admin_routers",
        "menu_type": "admin",
        "options": [
            {"text": "📶 کنترل پهنای باند", "callback_data": "bandwidth_control"},
            {"text": "🌐 پیکربندی شبکه", "callback_data": "network_config"},
            {"text": "⏱️ زمانبندی وظایف", "callback_data": "router_scheduler"},
            {"text": "📥 پشتیبان‌گیری پیکربندی", "callback_data": "router_backup"},
        ],
    },
    # System Control Menu
    "system_control": {
        "text": "🖥️ پنل کنترل سیستم",
        "row_width": [2, 2, 1],
        "back": "admins_main_menu",
        "menu_type": "admin",
        "options": [
            {"text": "🔄 راه‌اندازی مجدد ربات", "callback_data": "restart_bot"},
            {"text": "📊 سلامت سیستم", "callback_data": "system_health"},
            {"text": "🔍 مشاهده لاگ‌ها", "callback_data": "view_logs"},
            {"text": "🧹 پاکسازی کش", "callback_data": "clear_cache"},
            {"text": "💾 پشتیبان‌گیری پایگاه داده", "callback_data": "backup_database"},
            {"text": "⚠️ حالت اضطراری", "callback_data": "emergency_mode"},
            {"text": "⚙️ تنظیمات سیستم", "callback_data": "system_settings"},
        ],
    },
    # System Settings Menu
    "system_settings": {
        "text": "⚙️ پنل تنظیمات سیستم",
        "row_width": [2, 2, 1],
        "back": "system_control",
        "menu_type": "admin",
        "options": [
            {"text": "💰 تنظیمات پرداخت", "callback_data": "payment_settings"},
        ],
    },
    # Traffic Monitor Submenu
    "traffic_monitor": {
        "text": "📈 مانیتورینگ ترافیک شبکه",
        "row_width": [2, 2, 1],
        "back": "admin_routers",
        "menu_type": "admin",
        "options": [
            {"text": "📊 ترافیک زنده", "callback_data": "live_traffic"},
            {"text": "📈 تاریخچه ترافیک", "callback_data": "traffic_history"},
            {"text": "👥 ترافیک کاربران", "callback_data": "user_traffic"},
            {"text": "⚠️ فعالیت غیرعادی", "callback_data": "unusual_traffic"},
            {"text": "📥 دانلود گزارش اکسل", "callback_data": "export_traffic_excel"},
        ],
    },
    # Power Management Submenu
    "power_management": {
        "text": "🔌 مدیریت برق روتر",
        "row_width": [2, 2],
        "back": "admin_routers",
        "menu_type": "admin",
        "options": [
            {"text": "🔄 راه‌اندازی مجدد روتر", "callback_data": "power_restart_router"},
            {"text": "⚡ روشن کردن", "callback_data": "power_on_router"},
            {"text": "🔌 خاموش کردن", "callback_data": "power_off_router"},
            {"text": "⏱️ زمانبندی راه‌اندازی مجدد", "callback_data": "schedule_restart"},
        ],
    },
    # Admin Dashboard Menu
    "admin_dashboard": {
        "text": "📊 داشبورد مدیریتی",
        "row_width": [2, 2, 1],
        "back": "admins_main_menu",
        "menu_type": "admin",
        "options": [
            {"text": "👥 آمار کاربران", "callback_data": "user_stats"},
            {"text": "💰 نمای کلی مالی", "callback_data": "financial_overview"},
            {"text": "📡 وضعیت سیستم", "callback_data": "system_status"},
            {"text": "🔄 سرویس‌های فعال", "callback_data": "active_services"},
            {"text": "⚠️ هشدارهای سیستم", "callback_data": "system_alerts"},
        ],
    },
    # System Reports Menu (New)
    "system_reports": {
        "text": "📈 گزارش‌های سیستم",
        "row_width": [2, 2, 1],
        "back": "admins_main_menu",
        "menu_type": "admin",
        "options": [
            {"text": "👥 گزارش کاربران", "callback_data": "users_report"},
            {"text": "💰 گزارش مالی", "callback_data": "financial_report"},
            {"text": "📡 گزارش روترها", "callback_data": "routers_report"},
            {"text": "🔄 گزارش سرویس‌ها", "callback_data": "services_report"},
            {"text": "⏱️ گزارش زمانی", "callback_data": "time_based_report"},
            {"text": "📊 گزارش عملکرد", "callback_data": "performance_report"},
        ],
    },
    # Users Report Submenu (New)
    "users_report": {
        "text": "👥 گزارش کاربران",
        "row_width": [2, 2, 1],
        "back": "system_reports",
        "menu_type": "admin",
        "options": [
            {"text": "👥 کاربران فعال", "callback_data": "active_users_report"},
            {"text": "🕒 کاربران منقضی", "callback_data": "expired_users_report"},
            {"text": "📊 آمار ثبت نام", "callback_data": "registration_stats"},
            {"text": "🌐 کاربران بر اساس روتر", "callback_data": "users_by_router"},
            {"text": "📥 دانلود گزارش اکسل", "callback_data": "export_users_excel"},
        ],
    },
    # Financial Report Submenu (New)
    "financial_report": {
        "text": "💰 گزارش مالی",
        "row_width": [2, 2, 1],
        "back": "system_reports",
        "menu_type": "admin",
        "options": [
            {"text": "💰 درآمد روزانه", "callback_data": "daily_income_report"},
            {"text": "💰 درآمد ماهانه", "callback_data": "monthly_income_report"},
            {"text": "💼 درآمد فروشندگان", "callback_data": "sellers_income_report"},
            {"text": "🔄 تراکنش‌های اخیر", "callback_data": "recent_transactions"},
            {"text": "📥 دانلود گزارش اکسل", "callback_data": "export_financial_excel"},
        ],
    },
    # Routers Report Submenu (New)
    "routers_report": {
        "text": "📡 گزارش روترها",
        "row_width": [2, 2, 1],
        "back": "system_reports",
        "menu_type": "admin",
        "options": [
            {"text": "📊 وضعیت کلی روترها", "callback_data": "routers_overview_report"},
            {"text": "⚠️ مشکلات روترها", "callback_data": "router_issues_report"},
            {"text": "📈 آمار عملکرد", "callback_data": "router_performance_stats"},
            {"text": "👥 توزیع کاربران", "callback_data": "user_distribution_routers"},
            {"text": "📥 دانلود گزارش اکسل", "callback_data": "export_routers_excel"},
        ],
    },
    # Services Report Submenu (New)
    "services_report": {
        "text": "🔄 گزارش سرویس‌ها",
        "row_width": [2, 2, 1],
        "back": "system_reports",
        "menu_type": "admin",
        "options": [
            {"text": "🔄 سرویس‌های فعال", "callback_data": "active_services_report"},
            {
                "text": "⏱️ سرویس‌های در حال انقضا",
                "callback_data": "expiring_services_report",
            },
            {"text": "📊 آمار سرویس‌ها", "callback_data": "services_statistics"},
            {"text": "💰 درآمد سرویس‌ها", "callback_data": "services_revenue"},
            {"text": "📥 دانلود گزارش اکسل", "callback_data": "export_services_excel"},
        ],
    },
    # Time-Based Report Submenu (New)
    "time_based_report": {
        "text": "⏱️ گزارش زمانی",
        "row_width": [2, 2, 1],
        "back": "system_reports",
        "menu_type": "admin",
        "options": [
            {"text": "📅 گزارش روزانه", "callback_data": "daily_report"},
            {"text": "📅 گزارش هفتگی", "callback_data": "weekly_report"},
            {"text": "📅 گزارش ماهانه", "callback_data": "monthly_report"},
            {"text": "📅 گزارش سالانه", "callback_data": "yearly_report"},
            {"text": "📅 گزارش دوره دلخواه", "callback_data": "custom_period_report"},
            {
                "text": "📥 دانلود گزارش اکسل",
                "callback_data": "export_time_report_excel",
            },
        ],
    },
    # Performance Report Submenu (New)
    "performance_report": {
        "text": "📊 گزارش عملکرد",
        "row_width": [2, 2, 1],
        "back": "system_reports",
        "menu_type": "admin",
        "options": [
            {"text": "💻 عملکرد سیستم", "callback_data": "system_performance_report"},
            {"text": "📡 عملکرد روترها", "callback_data": "router_performance_report"},
            {
                "text": "🔄 عملکرد سرویس‌ها",
                "callback_data": "service_performance_report",
            },
            {
                "text": "👤 عملکرد فروشندگان",
                "callback_data": "seller_performance_report",
            },
            {
                "text": "📥 دانلود گزارش اکسل",
                "callback_data": "export_performance_excel",
            },
        ],
    },
    "users_main_menu": {
        "text": "📁 به پنل کاربری خوش آمدید. یکی از موارد زیر را انتخاب کنید.",
        "row_width": [1, 1, 1, 1, 1],
        "menu_type": "user",
        "options": [
            {"text": "👤 پروفایل من", "callback_data": "my_profile"},
            {"text": "👥 مدیریت کاربران", "callback_data": "manage_services"},
            {"text": "📡 وضعیت سرورها", "callback_data": "routers"},
            {"text": "💰 مدیرت مالی", "callback_data": "finance"},
            {"text": "☎️ پشتیبانی", "url": "https://t.ne/BlueNet1"},
        ],
    },
    "manage_services": {
        "text": "👥 یکی از موارد زیر را انتخاب کنید.",
        "back": "users_main_menu",
        "menu_type": "user",
        "options": [
            {"text": "➕ ایجاد کاربر", "callback_data": "create_service"},
            {"text": "👥 کاربران من", "callback_data": "my_services"},
            {"text": "📊 گزارشات", "callback_data": "reports"},
        ],
    },
    "reports": {
        "text": "یکی از موارد زیر را انتخاب کنید.",
        "back": "manage_services",
        "menu_type": "user",
        "options": [
            {
                "text": "🔔 کاربران در حال انقضا ",
                "callback_data": "show_expiring_services",
            },
        ],
    },
    "create_service": {
        "text": "🔒 یکی از موارد زیر را انتخاب کنید.",
        "row_width": [1, 1],
        "back": "manage_services",
        "menu_type": "user",
        "options": [
            {"text": "ای پی داینامیک", "callback_data": "dynamic"},
            {"text": "ای پی ثابت", "callback_data": "fixed"},
        ],
    },
    "my_services": {
        "text": "🔍 یکی از موارد زیر را انتخاب کنید.",
        "row_width": [1, 1, 1],
        "back": "manage_services",
        "menu_type": "user",
        "options": [
            {"text": "📜 مشاهده همه کاربران", "callback_data": "services"},
            {"text": "🔍 جستجو با نام کاربری", "callback_data": "find_name"},
            {"text": "🔍 جستجو با آدرس IP", "callback_data": "find_ip"},
        ],
    },
    "finance": {
        "text": "💰 یکی از موارد زیر را انتخاب کنید.",
        "row_width": [1, 1],
        "back": "users_main_menu",
        "menu_type": "user",
        "options": [
            {"text": "📑 تراکنش ها", "callback_data": "transactions"},
            {"text": "📤 درخواست تسویه حساب", "callback_data": "settlement"},
        ],
    },
}


async def create_markup(
    menu_key: str,
    user_role: UserRole,
) -> Tuple[Optional[InlineKeyboardMarkup], Optional[str]]:
    menu = menu_structure.get(menu_key)
    if not menu:
        return None, None

    # Check user's role
    menu_type = menu.get("menu_type", "user")

    # Verify access permissions
    if menu_type == "admin" and user_role != UserRole.ADMIN:
        # Return a restricted access message and markup
        return (
            InlineKeyboardBuilder()
            .button(text="🔙 بازگشت به منوی اصلی", callback_data="users_main_menu")
            .as_markup(),
            "⛔️ شما دسترسی به این بخش را ندارید.",
        )

    options = menu["options"]
    menu_text = menu["text"]
    keyboard = InlineKeyboardBuilder()

    # Add buttons based on the options
    for option in options:
        text = option["text"]
        kwargs = {
            "url": option.get("url"),
            "web_app": (
                WebAppInfo(url=option["web_app"]) if "web_app" in option else None
            ),
            "switch_inline_query": option.get("switch_inline_query"),
            "callback_data": option.get("callback_data", "default"),
        }
        keyboard.button(text=text, **{k: v for k, v in kwargs.items() if v is not None})

    # Adjust button rows according to defined row_width
    if "row_width" in menu:
        keyboard.adjust(*menu["row_width"])
    else:
        keyboard.adjust(2)

    # Add back button if specified
    if "back" in menu:
        keyboard.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data=menu["back"]))

    return keyboard.as_markup(), menu_text
