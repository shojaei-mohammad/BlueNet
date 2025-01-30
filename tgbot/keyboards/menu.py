from typing import Tuple, Optional

from aiogram.types import InlineKeyboardMarkup, WebAppInfo, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

menu_structure = {
    "users_main_menu": {
        "text": "🕋 به پنل کاربری خوش آمدید. یکی از موارد زیر را انتخاب کنید.",
        "row_width": [1, 1, 1, 1],
        "menu_type": "user",
        "options": [
            {"text": "🤑کسب درآمد", "callback_data": "earning"},
            {"text": "🛒 تست رایگان و خرید سرویس", "callback_data": "buy"},
            {"text": "📚 آموزش فعال‌سازی", "callback_data": "how_to's"},
            {"text": "🗃 سرویس‌های من", "callback_data": "my_services"},
        ],
    },
    "buy": {
        "text": "🕋 به پنل خرید خوش آمدید. یکی از موارد زیر را انتخاب کنید.",
        "row_width": [2, 1, 1],
        "menu_type": "user",
        "back": "users_main_menu",
        "options": [
            {"text": "🤑خرید سرور", "callback_data": "server"},
            {"text": "🛒 خرید VPN 1", "callback_data": "vpn"},
            {"text": "🛒 خرید VPN 2", "callback_data": "vpn"},
            {"text": "🛒 خرید VPN 3", "callback_data": "vpn"},
        ],
    },
}


async def create_markup(
    menu_key: str,
) -> Tuple[Optional[InlineKeyboardMarkup], Optional[str]]:
    menu = menu_structure.get(menu_key)
    if not menu:
        return None, None

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
        keyboard.adjust(2)  # Default to 2 buttons per row if not specified

    # Explicitly add a "back" navigation button on a new row
    if "back" in menu:
        # Create a new row specifically for the back button
        keyboard.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data=menu["back"]))

    return keyboard.as_markup(), menu_text
