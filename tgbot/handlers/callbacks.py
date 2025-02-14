# tgbot/handlers/callbacks.py
import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from infrastructure.database.models.sellers import Seller
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import Config
from tgbot.handlers.helper.profile import handle_my_profile
from tgbot.handlers.helper.purchase import handle_purchase
from tgbot.handlers.helper.tariffs import (
    handle_dynamic_tariffs,
    handle_fixed_tariffs,
    handle_fixed_country,
)
from tgbot.keyboards.menu import menu_structure, create_markup

callback_router = Router()


@callback_router.callback_query()
async def default_callback_query(
    callback: CallbackQuery,
    state: FSMContext,
    repo: RequestsRepo,
    config: Config,
    seller: Seller,
):
    try:
        callback_data = callback.data
        logging.info(
            f"Received callback data: {callback_data} from seller: {seller.id}"
        )

        if callback_data in menu_structure:
            markup, menu_text = await create_markup(callback_data, seller.user_role)
            await callback.message.edit_text(text=menu_text, reply_markup=markup)
        elif callback_data == "my_profile":
            await handle_my_profile(callback, seller)
        elif callback_data == "dynamic":
            await handle_dynamic_tariffs(callback, repo)
        elif callback_data == "fixed":
            await handle_fixed_tariffs(callback, repo)
        elif callback_data.startswith("fixed_country_"):
            await handle_fixed_country(callback, repo)
        elif callback_data.startswith("purchase_"):

            await handle_purchase(callback, repo, config.tg_bot.admin_ids, seller)
        else:
            logging.warning(f"Undefined callback: {callback_data}")
            await callback.answer(text="منو تعریف نشده است.")
    except TelegramBadRequest as e:
        logging.error(f"Telegram API error: {e}", exc_info=True)
        await callback.answer(
            "⚠️ خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.", show_alert=True
        )
        await state.clear()
    except Exception as e:
        logging.error(f"Unexpected error in callback handler: {e}", exc_info=True)
        await callback.answer(
            "⚠️ متأسفانه مشکلی پیش آمده. لطفاً دوباره تلاش کنید.", show_alert=True
        )
        await state.clear()
