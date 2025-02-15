# tgbot/handlers/services.py

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models import Service, ServiceStatus
from infrastructure.database.models.sellers import Seller
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.back_button import add_return_buttons
from tgbot.services.utils import convert_english_digits_to_farsi

services_router = Router()

SERVICES_PER_PAGE = 5


def is_service_online(service: Service) -> bool:
    """Check if service is online based on last_handshake"""
    if not service.last_handshake:
        return False
    # Consider service online if last handshake was within last 3 minutes
    return datetime.now(timezone.utc) - service.last_handshake < timedelta(minutes=3)


def create_services_keyboard(
    services: list[Service], page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Add service buttons
    for service in services:
        # Create status emoji based on service status and last handshake
        is_online = is_service_online(service)
        status_emoji = (
            "🟢" if service.status == ServiceStatus.ACTIVE and is_online else "🔴"
        )

        # Format service info using public_id
        service_info = (
            f"{status_emoji} {service.peer.public_id if service.peer else 'N/A'}"
        )

        builder.add(
            InlineKeyboardButton(
                text=service_info, callback_data=f"service_{service.id}"
            )
        )

    builder.adjust(1)  # One button per row

    # Add pagination buttons if needed
    if total_pages > 1:
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"services:{page-1}")
            )

        pagination_buttons.append(
            InlineKeyboardButton(
                text=f"📄 {page}/{total_pages}", callback_data="ignore"
            )
        )

        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(text="➡️", callback_data=f"services:{page+1}")
            )

        builder.row(*pagination_buttons)

    # Add back button using helper
    add_return_buttons(builder, "my_services", include_main_menu=True)

    return builder.as_markup()


@services_router.callback_query(F.data == "services")
async def show_services_list(
    callback: CallbackQuery, seller: Seller, repo: RequestsRepo
):
    """Handle services list display."""
    try:
        # Get paginated services and total count
        services, total_count = await repo.services.get_seller_services(
            seller_id=seller.id, page=1, per_page=SERVICES_PER_PAGE
        )

        # Calculate total pages
        total_pages = (total_count + SERVICES_PER_PAGE - 1) // SERVICES_PER_PAGE

        # Create message text
        active_count = sum(1 for s in services if s.status == ServiceStatus.ACTIVE)
        inactive_count = sum(1 for s in services if s.status == ServiceStatus.INACTIVE)

        text = (
            f"📋 لیست سرویس‌های شما:\n\n"
            f"🔢 تعداد کل: {convert_english_digits_to_farsi(total_count)}\n"
            f"✅ فعال: {convert_english_digits_to_farsi(active_count)}\n"
            f"⚠️  غیرفعال: {convert_english_digits_to_farsi(inactive_count)}\n\n"
            "برای مشاهده جزئیات هر سرویس روی آن کلیک کنید:"
        )

        # Send or edit message with keyboard
        await callback.message.edit_text(
            text=text,
            reply_markup=create_services_keyboard(
                services, page=1, total_pages=total_pages
            ),
        )

    except Exception as e:
        logging.error(f"Error in show_services_list: {e}", exc_info=True)
        await callback.answer(
            "❌ خطا در نمایش لیست سرویس‌ها. لطفاً دوباره تلاش کنید.", show_alert=True
        )


@services_router.callback_query(F.data.startswith("services:"))
async def handle_services_pagination(
    callback: CallbackQuery, seller: Seller, repo: RequestsRepo
):
    """Handle services pagination."""
    try:
        page = int(callback.data.split(":")[1])

        # Get paginated services and total count
        services, total_count = await repo.services.get_seller_services(
            seller_id=seller.id, page=page, per_page=SERVICES_PER_PAGE
        )

        # Calculate total pages
        total_pages = (total_count + SERVICES_PER_PAGE - 1) // SERVICES_PER_PAGE

        # Update message with new page
        active_count = sum(1 for s in services if s.status == ServiceStatus.ACTIVE)
        text = (
            f"📋 لیست سرویس‌های شما:\n\n"
            f"🔢 تعداد کل: {total_count}\n"
            f"✅ فعال: {active_count}\n\n"
            "برای مشاهده جزئیات هر سرویس روی آن کلیک کنید:"
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=create_services_keyboard(services, page, total_pages),
        )

    except Exception as e:
        logging.error(f"Error in handle_services_pagination: {e}", exc_info=True)
        await callback.answer(
            "❌ خطا در تغییر صفحه. لطفاً دوباره تلاش کنید.", show_alert=True
        )
