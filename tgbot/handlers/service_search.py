# tgbot/handlers/service_search.py
import logging
from ipaddress import ip_address

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models import Seller
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.handlers.service_details import (
    format_service_details,
    create_service_details_keyboard,
)
from tgbot.services.back_button import add_return_buttons
from tgbot.states.search import SearchStates

search_router = Router()


def is_valid_ip(ip_string: str) -> bool:
    """Validate IP address format."""
    try:
        ip_address(ip_string)
        return True
    except ValueError:
        return False


@search_router.callback_query(F.data == "find_name")
async def start_public_id_search(callback: CallbackQuery, state: FSMContext):
    """Start search by public ID process."""
    await state.set_state(SearchStates.WAITING_FOR_PUBLIC_ID)

    kb = InlineKeyboardBuilder()
    markup = add_return_buttons(kb, "my_services")

    prompt_message = await callback.message.edit_text(
        "🔍 لطفاً شناسه عمومی سرویس مورد نظر را وارد کنید:", reply_markup=markup
    )
    await state.update_data(prompt_message_id=prompt_message.message_id)
    await callback.answer()


@search_router.callback_query(F.data == "find_ip")
async def start_ip_search(callback: CallbackQuery, state: FSMContext):
    """Start search by IP process."""
    await state.set_state(SearchStates.WAITING_FOR_IP)

    kb = InlineKeyboardBuilder()
    markup = add_return_buttons(kb, "my_services")

    prompt_message = await callback.message.edit_text(
        "🌐 لطفاً IP سرویس مورد نظر را وارد کنید:", reply_markup=markup
    )
    await state.update_data(prompt_message_id=prompt_message.message_id)
    await callback.answer()


@search_router.message(SearchStates.WAITING_FOR_PUBLIC_ID)
async def handle_public_id_search(
    message: Message, state: FSMContext, seller: Seller, repo: RequestsRepo
):
    """Handle public ID search input."""
    try:
        public_id = message.text.strip()
        # Delete user's input message
        await message.delete()
        # Delete the prompt message
        state_data = await state.get_data()
        if prompt_message_id := state_data.get("prompt_message_id"):
            try:
                await message.bot.delete_message(message.chat.id, prompt_message_id)
            except Exception as e:
                logging.warning(f"Failed to delete prompt message: {e}")

        service = await repo.services.get_service_by_public_id(seller.id, public_id)

        if not service:
            kb = InlineKeyboardBuilder()
            markup = add_return_buttons(kb, "my_services")
            await message.answer(
                "❌ سرویسی با این شناسه عمومی یافت نشد.", reply_markup=markup
            )
            return

        await state.clear()

        await message.answer(
            text=format_service_details(service),
            reply_markup=create_service_details_keyboard(service),
        )

    except Exception as e:
        logging.error(f"Error in handle_public_id_search: {e}", exc_info=True)
        kb = InlineKeyboardBuilder()
        markup = add_return_buttons(kb, "my_services")
        await message.answer("❌ خطا در جستجوی سرویس.", reply_markup=markup)


@search_router.message(SearchStates.WAITING_FOR_IP)
async def handle_ip_search(
    message: Message, state: FSMContext, seller: Seller, repo: RequestsRepo
):
    """Handle IP search input."""
    try:
        ip = message.text.strip()
        # Delete user's input message
        await message.delete()
        # Delete the prompt message
        state_data = await state.get_data()
        if prompt_message_id := state_data.get("prompt_message_id"):
            try:
                await message.bot.delete_message(message.chat.id, prompt_message_id)
            except Exception as e:
                logging.warning(f"Failed to delete prompt message: {e}")

        if not is_valid_ip(ip):
            kb = InlineKeyboardBuilder()
            markup = add_return_buttons(kb, "my_services")
            await message.answer(
                "❌ فرمت IP وارد شده نامعتبر است. لطفاً دوباره تلاش کنید.",
                reply_markup=markup,
            )
            return

        service = await repo.services.get_service_by_ip(seller.id, ip)

        if not service:
            kb = InlineKeyboardBuilder()
            markup = add_return_buttons(kb, "my_services")
            await message.answer("❌ سرویسی با این IP یافت نشد.", reply_markup=markup)
            return

        await state.clear()

        await message.answer(
            text=format_service_details(service),
            reply_markup=create_service_details_keyboard(service),
        )

    except Exception as e:
        logging.error(f"Error in handle_ip_search: {e}", exc_info=True)
        kb = InlineKeyboardBuilder()
        markup = add_return_buttons(kb, "my_services")
        await message.answer("❌ خطا در جستجوی سرویس.", reply_markup=markup)
