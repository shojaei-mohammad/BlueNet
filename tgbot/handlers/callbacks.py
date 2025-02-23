# tgbot/handlers/callbacks.py
import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models.sellers import Seller
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import Config
from tgbot.handlers.helper.profile import handle_my_profile
from tgbot.handlers.helper.purchase import handle_purchase, handle_bulk_purchase
from tgbot.handlers.helper.tariffs import (
    handle_dynamic_tariffs,
    handle_fixed_tariffs,
    handle_fixed_country,
)
from tgbot.keyboards.menu import menu_structure, create_markup
from tgbot.states.purchase import PurchaseState

callback_router = Router()


@callback_router.message(PurchaseState.SELECTING_QUANTITY)
async def process_custom_quantity(
    message: Message,
    state: FSMContext,
    repo: RequestsRepo,
    config: Config,
    seller: Seller,
):
    try:
        quantity = int(message.text)
        if not 1 <= quantity <= 50:
            await message.answer("لطفاً عددی بین 1 تا 50 وارد کنید.")
            return

        data = await state.get_data()
        tariff_id = data["tariff_id"]
        await state.clear()

        callback_data = f"purchase_{tariff_id}_{quantity}"
        # Create a dummy callback query for compatibility
        dummy_callback = CallbackQuery(
            id="0",
            from_user=message.from_user,
            chat_instance="0",
            message=message,
            data=callback_data,
        )
        await handle_bulk_purchase(
            dummy_callback, repo, config.tg_bot.admin_ids, seller, quantity
        )

    except ValueError:
        await message.answer("لطفاً یک عدد معتبر وارد کنید.")
    except Exception as e:
        logging.error(f"Error in custom quantity handler: {e}")
        await message.answer("خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.")


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
            await handle_dynamic_tariffs(callback, repo, seller)
        elif callback_data == "fixed":
            await handle_fixed_tariffs(callback, repo)
        elif callback_data.startswith("fixed_country_"):
            await handle_fixed_country(callback, repo, seller)
        elif callback_data.startswith("purchase_"):
            # Split the callback data
            parts = callback.data.split("_")

            if len(parts) == 3:  # Format: purchase_[tariff_id]_[quantity]
                # This is a bulk purchase
                try:
                    quantity = int(parts[2])
                    await handle_bulk_purchase(
                        callback, repo, config.tg_bot.admin_ids, seller, quantity
                    )
                except ValueError:
                    await callback.answer(
                        "خطا در پردازش تعداد سفارش. لطفاً دوباره تلاش کنید.",
                        show_alert=True,
                    )
            elif len(parts) == 2:  # Format: purchase_[tariff_id]
                # This is a single purchase
                await handle_purchase(callback, repo, config.tg_bot.admin_ids, seller)
            else:
                await callback.answer("فرمت درخواست نامعتبر است.", show_alert=True)
        elif callback_data.startswith("custom_quantity_"):
            tariff_id = callback_data.split("_")[2]
            await state.set_state(PurchaseState.SELECTING_QUANTITY)
            await state.update_data(tariff_id=tariff_id)
            await callback.message.answer(
                "لطفاً تعداد مورد نظر را وارد کنید (حداکثر 50):"
            )
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
