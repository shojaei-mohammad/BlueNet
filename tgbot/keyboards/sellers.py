from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models import SellerStatus, Seller
from tgbot.services.back_button import add_return_buttons


def get_seller_status_emoji(seller: Seller) -> str:
    """
    Get emoji representing seller status

    Args:
        seller: Seller object

    Returns:
        Emoji string
    """
    if seller.status == SellerStatus.PENDING:
        return "⏳"
    elif seller.status == SellerStatus.APPROVED:
        return "✅" if seller.is_active else "⚠️"
    elif seller.status == SellerStatus.SUSPENDED:
        return "⚠️"
    elif seller.status == SellerStatus.BANNED:
        return "🚫"
    else:
        return "❓"


def create_seller_detail_keyboard(seller: Seller) -> InlineKeyboardMarkup:
    """
    Create keyboard for seller detail view

    Args:
        seller: Seller object

    Returns:
        InlineKeyboardMarkup with seller management buttons
    """
    builder = InlineKeyboardBuilder()

    # Add action buttons based on current seller status
    if seller.status == SellerStatus.PENDING:
        builder.button(text="✅ تایید", callback_data=f"confirm_seller_{seller.id}")
        builder.button(text="❌ رد", callback_data=f"reject_seller_{seller.id}")
    elif seller.status == SellerStatus.APPROVED:
        if seller.is_active:
            builder.button(text="⚠️ تعلیق", callback_data=f"seller_suspend_{seller.id}")
            builder.button(text="🚫 مسدود", callback_data=f"seller_ban_{seller.id}")
        else:
            builder.button(
                text="✅ فعال‌سازی", callback_data=f"seller_activate_{seller.id}"
            )
    elif seller.status == SellerStatus.SUSPENDED:
        builder.button(text="✅ فعال‌سازی", callback_data=f"seller_activate_{seller.id}")
        builder.button(text="🚫 مسدود", callback_data=f"seller_ban_{seller.id}")
    elif seller.status == SellerStatus.BANNED:
        builder.button(text="✅ رفع مسدودیت", callback_data=f"seller_unban_{seller.id}")

    # Add settings buttons
    builder.button(
        text="📊 تغییر درصد تخفیف", callback_data=f"seller_discount_{seller.id}"
    )
    builder.button(text="💰 تغییر سقف بدهی", callback_data=f"seller_debt_{seller.id}")

    # Add services button
    builder.button(
        text="📋 مشاهده سرویس‌ها", callback_data=f"seller_services_{seller.id}"
    )

    # Add message button
    builder.button(text="📨 ارسال پیام", callback_data=f"seller_message_{seller.id}")

    builder.button(
        text="🤯 غیرفعال کردن همه سرویس ها",
        callback_data=f"seller_disable_services_{seller.id}",
    )
    builder.button(
        text="😎 فعال کردن همه سرویس ها",
        callback_data=f"seller_enable_services_{seller.id}",
    )

    # Adjust layout: 2 buttons per row for actions, 1 button per row for others
    builder.adjust(2, 1, 1, 1, 1, 1, 1)
    markup = add_return_buttons(builder, "sellers")

    return markup


def create_sellers_keyboard(
    sellers: List[Seller], page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """
    Create keyboard with seller buttons and pagination

    Args:
        sellers: List of seller objects to display
        page: Current page number
        total_pages: Total number of pages

    Returns:
        Inline keyboard markup
    """
    builder = InlineKeyboardBuilder()

    # Add seller buttons
    for seller in sellers:
        status_emoji = get_seller_status_emoji(seller)
        seller_info = f"{status_emoji} {seller.username or seller.full_name}"
        builder.button(text=seller_info, callback_data=f"seller_view_{seller.id}")

    builder.adjust(1)  # One button per row

    # Add pagination buttons if needed
    if total_pages > 1:
        pagination_row = []
        if page > 1:
            pagination_row.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"sellers:{page - 1}")
            )

        pagination_row.append(
            InlineKeyboardButton(
                text=f"📄 {page}/{total_pages}", callback_data="ignore"
            )
        )

        if page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(text="➡️", callback_data=f"sellers:{page + 1}")
            )

        builder.row(*pagination_row)

    # Add search button
    builder.row(InlineKeyboardButton(text="🔍 جستجو", callback_data="sellers_search"))

    # Add back button using helper
    add_return_buttons(builder, "admins_main_menu", include_main_menu=True)

    return builder.as_markup()
