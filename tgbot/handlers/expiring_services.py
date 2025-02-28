# tgbot/handlers/expiring_services.py

import logging
from datetime import datetime, timedelta

from aiogram import Router, html, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models.sellers import Seller
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.back_button import add_return_buttons
from tgbot.services.utils import convert_to_shamsi

expiring_services_router = Router()


# Define states for expiring services view
class ExpiringServicesStates(StatesGroup):
    viewing = State()


# Constants
PAGE_SIZE = 5


def create_expiring_services_keyboard(services, page, total_pages, seller_id):
    """Create keyboard with buttons for expiring services and pagination."""
    builder = InlineKeyboardBuilder()

    # Add service buttons - one per row
    for service in services:
        # Use public_id as button text, or a fallback if not available
        button_text = (
            service.peer.public_id
            if service.peer and service.peer.public_id
            else f"Service #{service.id}"
        )
        builder.button(text=button_text, callback_data=f"service_view_{service.id}")

    # Add pagination buttons if needed
    if total_pages > 1:
        row = []

        # Previous page button
        if page > 1:
            row.append(
                InlineKeyboardBuilder()
                .button(text="◀️ قبلی", callback_data=f"exp_page_{seller_id}_{page-1}")
                .as_markup()
                .inline_keyboard[0][0]
            )

        # Page indicator
        row.append(
            InlineKeyboardBuilder()
            .button(text=f"صفحه {page} از {total_pages}", callback_data="exp_ignore")
            .as_markup()
            .inline_keyboard[0][0]
        )

        # Next page button
        if page < total_pages:
            row.append(
                InlineKeyboardBuilder()
                .button(text="بعدی ▶️", callback_data=f"exp_page_{seller_id}_{page+1}")
                .as_markup()
                .inline_keyboard[0][0]
            )

        builder.row(*row)

    # Add return buttons
    return add_return_buttons(builder, "finance", include_main_menu=True)


async def get_seller_expiring_services_paginated(
    repo, seller_id, days=3, page=1, page_size=PAGE_SIZE
):
    """
    Get paginated list of services that will expire in the specified number of days for a specific seller.

    Args:
        repo: Repository instance
        seller_id: ID of the seller
        days: Number of days until expiry (default: 3)
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Tuple of (list of services, total count)
    """
    try:
        # First get all services expiring in the specified days
        all_expiring_services = await repo.services.get_services_expiring_soon(
            days_threshold=days
        )

        # Filter for the specific seller
        seller_services = [s for s in all_expiring_services if s.seller_id == seller_id]

        # Get total count
        total_count = len(seller_services)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_services = seller_services[start_idx:end_idx]

        return paginated_services, total_count

    except Exception as e:
        logging.error(f"Error in get_seller_expiring_services_paginated: {str(e)}")
        raise


@expiring_services_router.callback_query(F.data == "show_expiring_services")
async def show_expiring_services_callback(
    callback: CallbackQuery, seller: Seller, repo: RequestsRepo, state: FSMContext
):
    """Show services that will expire in 3 days."""
    try:
        logging.info("Expiring services callback received")

        # Set state
        await state.set_state(ExpiringServicesStates.viewing)
        await state.update_data(seller_id=seller.id)

        # Get first page of expiring services
        page = 1
        services, total_count = await get_seller_expiring_services_paginated(
            repo=repo, seller_id=seller.id, days=3, page=page, page_size=PAGE_SIZE
        )

        # Calculate total pages
        total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
        if total_pages == 0:
            total_pages = 1

        # Generate text
        expiry_date = datetime.now().date() + timedelta(days=3)
        expiry_date_str = convert_to_shamsi(expiry_date)

        if services:
            text = (
                f"⚠️ {html.bold('سرویس‌های در حال انقضا')}\n\n"
                f"سرویس‌های زیر در تاریخ {html.bold(expiry_date_str)} منقضی خواهند شد.\n"
                f"برای مشاهده جزئیات هر سرویس روی آن کلیک کنید.\n\n"
                f"تعداد: {total_count} سرویس"
            )
        else:
            text = "✅ هیچ سرویسی در 3 روز آینده منقضی نخواهد شد."

        # Create keyboard
        keyboard = create_expiring_services_keyboard(
            services, page, total_pages, seller.id
        )

        # Send message
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in show_expiring_services_callback: {e}", exc_info=True)
        await callback.answer(
            "❌ خطا در دریافت لیست سرویس‌های در حال انقضا.", show_alert=True
        )
        await state.clear()


@expiring_services_router.callback_query(F.data.startswith("exp_page_"))
async def handle_expiring_services_pagination(
    callback: CallbackQuery, seller: Seller, repo: RequestsRepo, state: FSMContext
):
    """Handle pagination for expiring services."""
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

        # Get services for the specified page
        services, total_count = await get_seller_expiring_services_paginated(
            repo=repo, seller_id=seller.id, days=3, page=page, page_size=PAGE_SIZE
        )

        # Calculate total pages
        total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
        if total_pages == 0:
            total_pages = 1

        # Generate text
        expiry_date = datetime.now().date() + timedelta(days=3)
        expiry_date_str = convert_to_shamsi(expiry_date)

        text = (
            f"⚠️ {html.bold('سرویس‌های در حال انقضا')}\n\n"
            f"سرویس‌های زیر در تاریخ {html.bold(expiry_date_str)} منقضی خواهند شد.\n"
            f"برای مشاهده جزئیات هر سرویس روی آن کلیک کنید.\n\n"
            f"تعداد: {total_count} سرویس"
        )

        # Create keyboard
        keyboard = create_expiring_services_keyboard(
            services, page, total_pages, seller.id
        )

        # Update message
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logging.error(
            f"Error in handle_expiring_services_pagination: {e}", exc_info=True
        )
        await callback.answer("❌ خطا در دریافت صفحه بعدی.", show_alert=True)


@expiring_services_router.callback_query(F.data == "exp_ignore")
async def handle_exp_ignore_callback(callback: CallbackQuery):
    """Handle ignore callback for page indicator button."""
    await callback.answer()
