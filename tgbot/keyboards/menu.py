from typing import Tuple, Optional

from aiogram.types import InlineKeyboardMarkup, WebAppInfo, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models.sellers import UserRole

menu_structure = {
    "admins_main_menu": {
        "text": "📁 به پنل کاربری خوش آمدید. یکی از موارد زیر را انتخاب کنید.",
        "row_width": [1, 1, 1, 1],
        "menu_type": "admin",
        "options": [
            {"text": "📨 ارسال پیام به فروشندگان", "callback_data": "sendMessage_all"},
            {"text": "🤝 مدیریت عاملان فروش", "callback_data": "manage_resellers"},
            {"text": "🔗 ایجاد لینک دسترسی", "callback_data": "generate_link"},
            {"text": "👀 مشاهده منو عاملان", "callback_data": "users_main_menu"},
        ],
    },
    "users_main_menu": {
        "text": "📁 به پنل کاربری خوش آمدید. یکی از موارد زیر را انتخاب کنید.",
        "row_width": [1, 1, 1, 1, 1],
        "menu_type": "user",
        "options": [
            {"text": "👤 پروفایل من", "callback_data": "my_profile"},
            {"text": "👥 مدیریت کاربران", "callback_data": "mng_usrs"},
            {"text": "📡 وضعیت سرورها", "callback_data": "rtr_state"},
            {"text": "💰 مدیرت مالی", "callback_data": "finance"},
            {"text": "☎️ پشتیبانی", "url": "https://t.ne/BlueNet1"},
        ],
    },
    "mng_usrs": {
        "text": "👥 یکی از موارد زیر را انتخاب کنید.",
        "back": "users_main_menu",
        "menu_type": "user",
        "options": [
            {"text": "➕ ایجاد کاربر", "callback_data": "add_vpn"},
            {"text": "👥 کاربران من", "callback_data": "my_usrs"},
            {"text": "📊 گزارشات", "callback_data": "reports"},
        ],
    },
    "reports": {
        "text": "یکی از موارد زیر را انتخاب کنید.",
        "back": "mng_usrs",
        "menu_type": "user",
        "options": [
            {"text": "🔔 کاربران در حال انقضا ", "callback_data": "rep_expire"},
        ],
    },
    "add_vpn": {
        "text": "🔒 یکی از موارد زیر را انتخاب کنید.",
        "row_width": [1, 1],
        "back": "mng_usrs",
        "menu_type": "user",
        "options": [
            {"text": "ای پی داینامیک", "callback_data": "dynamic"},
            {"text": "ای پی ثابت", "callback_data": "fixed"},
        ],
    },
    "dynamic": {
        "text": "🔒 یکی از موارد زیر را انتخاب کنید.",
        "row_width": [1, 1],
        "back": "add_vpn",
        "menu_type": "user",
        "options": [
            {"text": "🚶‍♂️ ایجاد کاربر تکی", "callback_data": "dynamic_single"},
            {"text": "👥 ایجاد کاربر انبوه", "callback_data": "dynamic_bulk"},
        ],
    },
    "fixed": {
        "text": "🔒 کشور مورد نظرتان را انتخاب نمایید.",
        "row_width": [2, 2, 2, 2],
        "back": "add_vpn",
        "menu_type": "user",
        "options": [
            {"text": "🇫🇮 فنلاند", "callback_data": "fixed_finland"},
            {"text": "🇳🇱 هلند", "callback_data": "fixed_netherlands"},
            {"text": "🇺🇸 آمریکا", "callback_data": "fixed_us"},
            {"text": "🇬🇧 انگلیس", "callback_data": "fixed_uk"},
            {"text": "🇹🇷 ترکیه", "callback_data": "fixed_turkey"},
            {"text": "🇦🇪 امارات", "callback_data": "fixed_uae"},
            {"text": "🇫🇷 فرانسه", "callback_data": "fixed_france"},
            {"text": "🇨🇦 کانادا", "callback_data": "fixed_canada"},
        ],
    },
    "my_usrs": {
        "text": "🔍 یکی از موارد زیر را انتخاب کنید.",
        "row_width": [1, 1, 1],
        "back": "mng_usrs",
        "menu_type": "user",
        "options": [
            {"text": "📜 مشاهده همه کاربران", "callback_data": "all_usr"},
            {"text": "🔍 جستجو با نام کاربری", "callback_data": "find_user"},
            {"text": "🔍 جستجو با آدرس IP", "callback_data": "find_ip"},
        ],
    },
    "finance": {
        "text": "💰 یکی از موارد زیر را انتخاب کنید.",
        "row_width": [1, 1],
        "back": "users_main_menu",
        "menu_type": "user",
        "options": [
            {"text": "📑 تراکنش ها", "callback_data": "transaction_repo"},
            {"text": "📤 درخواست تسویه حساب", "callback_data": "debit"},
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
