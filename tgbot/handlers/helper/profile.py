import logging

from aiogram import html
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tgbot.services.back_button import add_return_buttons
from tgbot.services.utils import format_currency, convert_english_digits_to_farsi


async def handle_my_profile(callback: CallbackQuery, seller):
    """Handle the 'my_profile' callback."""
    try:
        full_name = seller.full_name
        total_services = convert_english_digits_to_farsi(seller.total_services)
        active_services = convert_english_digits_to_farsi(seller.active_services)
        total_profit = format_currency(seller.total_profit, True)
        discount_percent = convert_english_digits_to_farsi(seller.discount_percent)
        current_debt = format_currency(seller.current_debt, True)
        debt_limit = format_currency(seller.debt_limit, True)

        profile_text = html.bold("👤 پروفایل من\n\n")
        profile_text += f"📌 {html.bold('نام کامل:')} {full_name}\n\n"
        profile_text += (
            f"📊 {html.bold('تعداد خدمات فروخته شده:')} {total_services}\n\n"
        )
        profile_text += f"📈 {html.bold('خدمات فعال:')} {active_services}\n\n"
        profile_text += f"💳 {html.bold('مجموع سود:')} {total_profit} تومان\n\n"
        profile_text += f"🎯 {html.bold('درصد تخفیف:')} {discount_percent}%\n\n"
        profile_text += f"📉 {html.bold('بدهی فعلی:')} {current_debt} تومان\n\n"
        profile_text += f"🚫 {html.bold('حد مجاز بدهی:')} {debt_limit} تومان\n\n"

        if seller.current_debt >= seller.debt_limit:
            profile_text += (
                "\n⚠️ شما به حد مجاز بدهی خود رسیده‌اید. لطفاً بدهی خود را تسویه کنید.\n\n"
            )

        kb = InlineKeyboardBuilder()
        kb.button(text="💳 تسویه حساب", callback_data="settle_debt")
        markup = add_return_buttons(kb_builder=kb, back_callback="users_main_menu")

        await callback.message.edit_text(text=profile_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"Error handling my_profile callback: {e}", exc_info=True)
        raise
