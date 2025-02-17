# tgbot/handlers/services.py

import logging

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


def get_service_status_emoji(service: Service) -> str:
    """Get appropriate emoji for service status."""
    if not service.status:
        return "❓"

    status_emojis = {
        ServiceStatus.UNUSED: "⚪",  # White circle for unused
        ServiceStatus.INACTIVE: "🔴",  # Red circle for inactive
        ServiceStatus.ACTIVE: "🟢",  # Green circle for active
        ServiceStatus.EXPIRED: "🟡",  # Yellow circle for expired
        ServiceStatus.DELETED: "⚫",  # Black circle for deleted
    }

    return status_emojis.get(service.status, "❓")


def create_services_keyboard(
    services: list[Service], page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Add service buttons
    for service in services:
        status_emoji = get_service_status_emoji(service)
        service_info = (
            f"{status_emoji} {service.peer.public_id if service.peer else 'N/A'}"
        )

        builder.add(
            InlineKeyboardButton(
                text=service_info, callback_data=f"service_view_{service.id}"
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

        # Count services by status
        status_counts = {status: 0 for status in ServiceStatus}
        for service in services:
            if service.status in status_counts:
                status_counts[service.status] += 1

        # Create message text
        text = (
            f"📋 لیست سرویس‌های شما:\n\n"
            f"🔢 تعداد کل: {convert_english_digits_to_farsi(total_count)}\n"
            f"🟢 فعال: {convert_english_digits_to_farsi(status_counts[ServiceStatus.ACTIVE])}\n"
            f"🔴 غیرفعال: {convert_english_digits_to_farsi(status_counts[ServiceStatus.INACTIVE])}\n"
            f"⚪ استفاده نشده: {convert_english_digits_to_farsi(status_counts[ServiceStatus.UNUSED])}\n"
            f"🟡 منقضی شده: {convert_english_digits_to_farsi(status_counts[ServiceStatus.EXPIRED])}\n"
            f"⚫ حذف شده: {convert_english_digits_to_farsi(status_counts[ServiceStatus.DELETED])}\n\n"
            "برای مشاهده جزئیات هر سرویس روی آن کلیک کنید:"
        )

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

        # Count services by status
        status_counts = {status: 0 for status in ServiceStatus}
        for service in services:
            if service.status in status_counts:
                status_counts[service.status] += 1

        # Update message with new page
        text = (
            f"📋 لیست سرویس‌های شما:\n\n"
            f"🔢 تعداد کل: {convert_english_digits_to_farsi(total_count)}\n"
            f"🟢 فعال: {convert_english_digits_to_farsi(status_counts[ServiceStatus.ACTIVE])}\n"
            f"🔴 غیرفعال: {convert_english_digits_to_farsi(status_counts[ServiceStatus.INACTIVE])}\n"
            f"⚪ استفاده نشده: {convert_english_digits_to_farsi(status_counts[ServiceStatus.UNUSED])}\n"
            f"🟡 منقضی شده: {convert_english_digits_to_farsi(status_counts[ServiceStatus.EXPIRED])}\n"
            f"⚫ حذف شده: {convert_english_digits_to_farsi(status_counts[ServiceStatus.DELETED])}\n\n"
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
