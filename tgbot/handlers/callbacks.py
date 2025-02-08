import logging

from aiogram import Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models.sellers import Seller
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.keyboards.menu import menu_structure, create_markup
from tgbot.services.back_button import add_return_buttons
from tgbot.services.utils import format_currency, convert_english_digits_to_farsi

callback_router = Router()


@callback_router.callback_query()
async def default_callback_query(
    callback: CallbackQuery,
    state: FSMContext,
    repo: RequestsRepo,
    seller: Seller,
):
    try:
        # Extract relevant data from the callback query
        callback_data = callback.data

        # Check if the received callback_data matches any menu defined in menu_structure
        if callback_data in menu_structure:
            # Generate the appropriate markup and text for the menu corresponding to callback_data
            markup, menu_text = await create_markup(callback_data, seller.user_role)
            await callback.message.edit_text(text=menu_text, reply_markup=markup)
        elif callback_data == "my_profile":
            # Format the seller's data for better readability
            full_name = seller.full_name
            total_services = convert_english_digits_to_farsi(seller.total_services)
            active_services = convert_english_digits_to_farsi(seller.active_services)
            total_profit = format_currency(seller.total_profit, True)
            discount_percent = convert_english_digits_to_farsi(seller.discount_percent)
            current_debt = format_currency(seller.current_debt, True)
            debt_limit = format_currency(seller.debt_limit, True)

            # Prepare the profile text with proper spacing
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

            # Check if the seller has exceeded their debt limit
            if seller.current_debt >= seller.debt_limit:
                profile_text += "\n⚠️ شما به حد مجاز بدهی خود رسیده‌اید. لطفاً بدهی خود را تسویه کنید.\n\n"

            # Create the settlement button with a return button
            kb = InlineKeyboardBuilder()
            kb.button(text="💳 تسویه حساب", callback_data="settle_debt")
            markup = add_return_buttons(kb_builder=kb, back_callback="users_main_menu")

            # Send the profile text with the settlement button
            await callback.message.edit_text(text=profile_text, reply_markup=markup)

        else:
            logging.info(f"undefined callback: {callback_data}")
            await callback.answer(text="منو تعریف نشده است.")
    except TelegramBadRequest as e:
        logging.error(f"Telegram API error: {e}")
        await callback.answer(
            "⚠️ خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.", show_alert=True
        )
        await state.clear()
    except Exception as e:
        logging.error(f"Unexpected error in callback handler: {e}")
        await callback.answer(
            "⚠️ متأسفانه مشکلی پیش آمده. لطفاً دوباره تلاش کنید.", show_alert=True
        )
        await state.clear()
