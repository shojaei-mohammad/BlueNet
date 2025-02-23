import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models import Seller, Transaction, TransactionType
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import Config
from tgbot.services.back_button import add_return_buttons
from tgbot.services.utils import format_currency
from tgbot.states.settlement import SettlementState

settlement_router = Router()


@settlement_router.callback_query(F.data == "settlement")
async def start_settlement(
    callback: CallbackQuery,
    seller: Seller,
    state: FSMContext,
    config: Config,
):
    """Handle initial settlement request."""
    try:
        if seller.current_debt <= 0:
            await callback.answer("شما در حال حاضر بدهی ندارید.", show_alert=True)
            return

        # Format the settlement information message
        message_text = (
            "💰 درخواست تسویه حساب\n\n"
            f"💵 مبلغ بدهی شما: {format_currency(seller.current_debt, convert_to_farsi=True)} تومان\n\n"
            "📝 راهنمای تسویه حساب:\n"
            f"1️⃣ مبلغ را به شماره کارت زیر واریز کنید:\n{config.tg_bot.card_number}\n"
            f"به نام: {config.tg_bot.card_holder}\n\n"
            "2️⃣ رسید پرداخت را به صورت عکس یا متن (شماره پیگیری) ارسال کنید.\n\n"
            "❌ برای انصراف روی /cancel کلیک کنید."
        )

        # Add back button
        kb = InlineKeyboardBuilder()
        markup = add_return_buttons(kb, "finance")

        await callback.message.edit_text(text=message_text, reply_markup=markup)
        await state.set_state(SettlementState.WAITING_FOR_RECEIPT)
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in start_settlement: {e}")
        await callback.answer(
            "خطا در شروع فرآیند تسویه. لطفا مجددا تلاش کنید.", show_alert=True
        )


@settlement_router.message(SettlementState.WAITING_FOR_RECEIPT)
async def handle_settlement_receipt(
    message: Message,
    state: FSMContext,
    seller: Seller,
    repo: RequestsRepo,
    config: Config,
):
    """Handle receipt submission from seller."""
    try:
        # Check for cancel command
        if message.text == "/cancel":
            kb = InlineKeyboardBuilder()
            markup = add_return_buttons(kb, "finance")
            await message.answer("❌ درخواست تسویه حساب لغو شد.", reply_markup=markup)
            await state.clear()
            return

        # Get receipt content (photo or text)
        if message.photo:
            file_id = message.photo[-1].file_id
            receipt_type = "photo"
            receipt_content = file_id
        elif message.text:
            receipt_type = "text"
            receipt_content = message.text
        else:
            await message.answer("❌ لطفا رسید را به صورت عکس یا متن ارسال کنید.")
            return

        # Create settlement transaction with proof
        transaction = Transaction(
            seller_id=seller.id,
            amount=seller.current_debt,
            transaction_type=TransactionType.SETTLEMENT,
            description=f"درخواست تسویه حساب به مبلغ {format_currency(seller.current_debt, convert_to_farsi=True)} تومان",
            proof=receipt_content,  # Save the receipt content as proof
        )
        transaction = await repo.transactions.create_transaction(transaction)

        # Notify admins
        admin_message = (
            "🔄 درخواست تسویه حساب جدید\n\n"
            f"👤 فروشنده: {seller.full_name}\n"
            f"💰 مبلغ: {format_currency(seller.current_debt, convert_to_farsi=True)} تومان\n"
            f"🔖 شناسه تراکنش: {transaction.id}\n"
            f"📝 نوع رسید: {'تصویر' if receipt_type == 'photo' else 'متنی'}"
        )

        # Create confirmation keyboard for admins
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ تایید", callback_data=f"confirm_settlement_{transaction.id}")
        kb.button(text="❌ رد", callback_data=f"reject_settlement_{transaction.id}")
        kb.adjust(2)

        # Send notification to admins
        for admin_id in config.tg_bot.admin_ids:
            try:
                if receipt_type == "photo":
                    await message.bot.send_photo(
                        chat_id=admin_id,
                        photo=receipt_content,
                        caption=admin_message,
                        reply_markup=kb.as_markup(),
                    )
                else:
                    await message.bot.send_message(
                        chat_id=admin_id,
                        text=f"{admin_message}\n\n📝 رسید پرداخت:\n{receipt_content}",
                        reply_markup=kb.as_markup(),
                    )
            except Exception as e:
                logging.error(f"Failed to notify admin {admin_id}: {e}")

        # Notify seller
        kb = InlineKeyboardBuilder()
        markup = add_return_buttons(kb, "finance")
        await message.answer(
            "✅ درخواست تسویه حساب شما ثبت شد و در انتظار تایید مدیر است.\n"
            "پس از بررسی به شما اطلاع داده خواهد شد.",
            reply_markup=markup,
        )
        await state.clear()

    except Exception as e:
        logging.error(f"Error in handle_settlement_receipt: {e}")
        kb = InlineKeyboardBuilder()
        markup = add_return_buttons(kb, "finance")
        await message.answer(
            "❌ خطا در ثبت درخواست. لطفا مجددا تلاش کنید.", reply_markup=markup
        )
        await state.clear()
