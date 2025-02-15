# tgbot/handlers/purchase_states.py
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models.sellers import Seller
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import Config
from tgbot.handlers.helper.purchase import handle_bulk_purchase
from tgbot.keyboards.purchase import get_bulk_purchase_keyboard
from tgbot.services.back_button import add_return_buttons
from tgbot.states.purchase import PurchaseState

purchase_router = Router()


@purchase_router.callback_query(F.data.startswith("select_quantity_"))
async def show_quantity_selection(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Show the bulk purchase keyboard when a tariff is selected"""
    try:
        tariff_id = callback.data.split("_")[2]
        markup = get_bulk_purchase_keyboard(tariff_id)
        await callback.message.edit_text(
            "👥 لطفاً تعداد کاربر مورد نظر را انتخاب کنید:", reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Error in show_quantity_selection: {e}")
        await callback.answer(
            "خطا در نمایش منوی انتخاب تعداد. لطفاً دوباره تلاش کنید.", show_alert=True
        )


@purchase_router.callback_query(F.data.startswith("custom_quantity_"))
async def handle_custom_quantity_request(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Handle request for custom quantity input"""
    try:
        tariff_id = callback.data.split("_")[2]
        await state.set_state(PurchaseState.SELECTING_QUANTITY)
        await state.update_data(tariff_id=tariff_id)
        await callback.message.edit_text(
            "🔢 لطفاً تعداد مورد نظر را وارد کنید (حداکثر 50):\n\n"
            "برای لغو عملیات، دستور /cancel را وارد کنید."
        )
    except Exception as e:
        logging.error(f"Error in handle_custom_quantity_request: {e}")
        await callback.answer(
            "خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.", show_alert=True
        )


@purchase_router.message(PurchaseState.SELECTING_QUANTITY)
async def process_custom_quantity(
    message: Message,
    state: FSMContext,
    repo: RequestsRepo,
    config: Config,
    seller: Seller,
):
    """Process custom quantity input"""
    try:
        # Check if the message is a cancel command
        if message.text.lower() == "/cancel":
            await state.clear()
            # Create a new keyboard for returning to tariffs
            kb = InlineKeyboardBuilder()
            markup = add_return_buttons(
                kb_builder=kb, back_callback="dynamic", include_main_menu=True
            )
            await message.answer(
                "❌ عملیات لغو شد.\n"
                "برای مشاهده لیست تعرفه‌ها، از دکمه‌های زیر استفاده کنید.",
                reply_markup=markup,
            )
            return

        # Validate quantity
        try:
            quantity = int(message.text)
        except ValueError:
            await message.answer("❌ لطفاً یک عدد معتبر وارد کنید.")
            return

        if not 1 <= quantity <= 50:
            await message.answer("❌ لطفاً عددی بین 1 تا 50 وارد کنید.")
            return

        # Get tariff_id from state
        data = await state.get_data()
        tariff_id = data["tariff_id"]
        await state.clear()

        # Create dummy callback for bulk purchase handler
        dummy_callback = CallbackQuery(
            id="0",
            from_user=message.from_user,
            chat_instance="0",
            message=message,
            data=f"purchase_{tariff_id}_{quantity}",
        )

        # Process the bulk purchase
        await handle_bulk_purchase(
            dummy_callback, repo, config.tg_bot.admin_ids, seller, quantity
        )

    except Exception as e:
        logging.error(f"Error in process_custom_quantity: {e}")
        await message.answer("❌ خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.")
        await state.clear()
