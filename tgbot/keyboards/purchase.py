# In tgbot/keyboards/purchase.py
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tgbot.services.back_button import add_return_buttons


def get_bulk_purchase_keyboard(tariff_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    # Add quantity options
    kb.button(text="۱ کاربر", callback_data=f"purchase_{tariff_id}_1")
    kb.button(text="۳ کاربر", callback_data=f"purchase_{tariff_id}_3")
    kb.button(text="۵ کاربر", callback_data=f"purchase_{tariff_id}_5")
    kb.button(text="۱۰ کاربر", callback_data=f"purchase_{tariff_id}_10")
    kb.button(text="تعداد دلخواه", callback_data=f"custom_quantity_{tariff_id}")

    kb.adjust(2)

    # Add return buttons
    return add_return_buttons(
        kb_builder=kb, back_callback="dynamic", include_main_menu=True
    )
