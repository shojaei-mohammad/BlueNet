# tgbot/handlers/transaction_history.py

import logging

from aiogram import Router, html, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models import TransactionType
from infrastructure.database.models.sellers import Seller
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.back_button import add_return_buttons
from tgbot.services.utils import convert_to_shamsi, format_currency

transaction_history_router = Router()


# Define states for transaction history
class TransactionHistoryStates(StatesGroup):
    viewing = State()


# Constants
PAGE_SIZE = 5
TRANSACTION_HISTORY_DAYS = 30


# Helper functions
def format_transaction_type(transaction_type):
    """Format transaction type to Persian."""
    if transaction_type == TransactionType.PURCHASE:
        return "خرید"
    elif transaction_type == TransactionType.RENEWAL:
        return "تمدید"
    elif transaction_type == TransactionType.SETTLEMENT:
        return "تسویه"
    return str(transaction_type)


def create_transactions_keyboard(seller_id: int, page: int, total_pages: int):
    """Create pagination keyboard for transactions."""
    builder = InlineKeyboardBuilder()

    # Add pagination buttons
    if page > 1:
        builder.button(text="◀️ قبلی", callback_data=f"tx_page_{seller_id}_{page-1}")

    # Page indicator
    builder.button(text=f"صفحه {page} از {total_pages}", callback_data="tx_ignore")

    if page < total_pages:
        builder.button(text="بعدی ▶️", callback_data=f"tx_page_{seller_id}_{page+1}")

    # Adjust layout
    if total_pages > 1:
        builder.adjust(3)
    else:
        builder.adjust(1)

    # Add return buttons
    return add_return_buttons(builder, "finance", include_main_menu=True)


def generate_transactions_text(transactions, page, total_pages, total_count):
    """Generate formatted text for transaction history."""
    if not transactions:
        return "📋 هیچ تراکنشی در 30 روز گذشته یافت نشد."

    text = f"📊 {html.bold('تاریخچه تراکنش‌های 30 روز گذشته')}\n\n"

    # Add summary at the top
    text += (
        f"📝 {html.bold('تعداد کل:')} {len(transactions)} از {total_count} تراکنش\n\n"
    )
    text += f"📄 {html.bold('صفحه')} {page}/{total_pages}\n\n"

    # Add transactions
    for i, tx in enumerate(transactions, 1):
        # Format date
        date_str = convert_to_shamsi(tx.created_at)

        # Format transaction type
        tx_type = format_transaction_type(tx.transaction_type)

        # Format amount with sign
        if tx.transaction_type == TransactionType.SETTLEMENT:
            amount_str = f"- {format_currency(tx.amount, convert_to_farsi=True)}"
        else:
            amount_str = f"+ {format_currency(tx.amount, convert_to_farsi=True)}"

        # Format description
        description = tx.description if tx.description else ""

        # Add to text
        text += f"{i}. {html.bold(date_str)} | {tx_type}\n"
        text += f"   {html.bold(amount_str)} تومان\n"
        if description:
            text += f"   {description}\n"
        text += "\n"

    return text


@transaction_history_router.callback_query(F.data == "transactions")
async def show_transactions_callback(
    callback: CallbackQuery, seller: Seller, repo: RequestsRepo, state: FSMContext
):
    """Show transaction history for the seller."""
    try:
        logging.info("Transaction history callback received")

        # Set state
        await state.set_state(TransactionHistoryStates.viewing)
        await state.update_data(seller_id=seller.id)

        # Get first page of transactions
        page = 1
        transactions, total_count = (
            await repo.transactions.get_seller_transactions_paginated(
                seller_id=seller.id,
                days=TRANSACTION_HISTORY_DAYS,
                page=page,
                page_size=PAGE_SIZE,
            )
        )

        # Calculate total pages
        total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
        if total_pages == 0:
            total_pages = 1

        # Generate text and keyboard
        text = generate_transactions_text(transactions, page, total_pages, total_count)
        keyboard = create_transactions_keyboard(seller.id, page, total_pages)

        # Send message
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in show_transactions_callback: {e}", exc_info=True)
        await callback.answer("❌ خطا در دریافت تاریخچه تراکنش‌ها.", show_alert=True)
        await state.clear()


@transaction_history_router.callback_query(F.data.startswith("tx_page_"))
async def handle_transactions_pagination(
    callback: CallbackQuery, seller: Seller, repo: RequestsRepo, state: FSMContext
):
    """Handle transaction history pagination."""
    try:
        # Parse callback data
        parts = callback.data.split("_")
        if len(parts) != 4:
            await callback.answer("داده نامعتبر")
            return

        seller_id = int(parts[2])
        page = int(parts[3])

        # Verify seller
        if seller_id != seller.id:
            await callback.answer(
                "❌ شما مجاز به مشاهده این اطلاعات نیستید.", show_alert=True
            )
            return

        # Get transactions for the specified page
        transactions, total_count = (
            await repo.transactions.get_seller_transactions_paginated(
                seller_id=seller.id,
                days=TRANSACTION_HISTORY_DAYS,
                page=page,
                page_size=PAGE_SIZE,
            )
        )

        # Calculate total pages
        total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
        if total_pages == 0:
            total_pages = 1

        # Generate text and keyboard
        text = generate_transactions_text(transactions, page, total_pages, total_count)
        keyboard = create_transactions_keyboard(seller.id, page, total_pages)

        # Update message
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in handle_transactions_pagination: {e}", exc_info=True)
        await callback.answer("❌ خطا در دریافت صفحه تراکنش‌ها.", show_alert=True)


@transaction_history_router.callback_query(F.data == "tx_ignore")
async def handle_ignore_callback(callback: CallbackQuery):
    """Handle ignore callback for page indicator button."""
    await callback.answer()
