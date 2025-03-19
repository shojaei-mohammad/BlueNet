import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Tuple

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models.sellers import Seller, SellerStatus
from infrastructure.database.models.services import ServiceStatus
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.admin import AdminFilter
from tgbot.keyboards.sellers import (
    create_seller_detail_keyboard,
    create_sellers_keyboard,
)
from tgbot.services.utils import convert_english_digits_to_farsi, format_currency
from tgbot.states.sellers import SellerManagementState

# Create router with admin filter
sellers_router = Router()
sellers_router.message.filter(AdminFilter())
sellers_router.callback_query.filter(AdminFilter())

# Number of sellers to display per page
SELLERS_PER_PAGE = 10


def format_seller_details_text(
    seller: Seller, service_stats: Dict[ServiceStatus, int]
) -> str:
    """
    Format seller details into a text message

    Args:
        seller: Seller object
        service_stats: Dictionary of service counts by status

    Returns:
        Formatted text message
    """
    # Format seller status
    status_emoji = {
        SellerStatus.PENDING: "⏳ در انتظار تایید",
        SellerStatus.APPROVED: "✅ تایید شده",
        SellerStatus.SUSPENDED: "⚠️ تعلیق شده",
        SellerStatus.BANNED: "🚫 مسدود شده",
    }.get(seller.status, "❓ نامشخص")

    # Format active status
    active_status = "✅ فعال" if seller.is_active else "❌ غیرفعال"

    # Calculate total services
    total_services = sum(service_stats.values())

    # Create message text
    return (
        f"👤 اطلاعات فروشنده:\n\n"
        f"🏷 شناسه: {seller.id}\n"
        f"👤 نام کاربری: {seller.username or '---'}\n"
        f"📝 نام کامل: {seller.full_name}\n"
        f"🚦 وضعیت: {status_emoji}\n"
        f"⚙️ حالت: {active_status}\n"
        f"💰 بدهی فعلی: {format_currency(seller.current_debt, convert_to_farsi=True)} تومان\n"
        f"💵 سقف بدهی: {format_currency(seller.debt_limit, convert_to_farsi=True)} تومان\n"
        f"📊 درصد تخفیف: {convert_english_digits_to_farsi(seller.discount_percent)}%\n"
        f"💹 کل فروش: {format_currency(seller.total_sale, convert_to_farsi=True)} تومان\n"
        f"📈 کل سود: {format_currency(seller.total_profit, convert_to_farsi=True)} تومان\n\n"
        f"📊 آمار سرویس‌ها:\n"
        f"🔢 تعداد کل: {convert_english_digits_to_farsi(total_services)}\n"
        f"🟢 فعال: {convert_english_digits_to_farsi(service_stats[ServiceStatus.ACTIVE])}\n"
        f"🔴 غیرفعال: {convert_english_digits_to_farsi(service_stats[ServiceStatus.INACTIVE])}\n"
        f"⚪ استفاده نشده: {convert_english_digits_to_farsi(service_stats[ServiceStatus.UNUSED])}\n"
        f"🟡 منقضی شده: {convert_english_digits_to_farsi(service_stats[ServiceStatus.EXPIRED])}\n"
        f"⚫ حذف شده: {convert_english_digits_to_farsi(service_stats[ServiceStatus.DELETED])}\n"
    )


async def get_seller_with_stats(
    repo: RequestsRepo, seller_id: int
) -> Tuple[Optional[Seller], Dict[ServiceStatus, int]]:
    """
    Helper function to get seller with service stats

    Args:
        repo: Repository instance
        seller_id: Seller ID

    Returns:
        Tuple of (seller, service_stats) or (None, {}) if seller not found
    """
    try:
        seller, service_stats = await repo.sellers.get_seller_with_service_stats(
            seller_id
        )
        return seller, service_stats
    except Exception as e:
        logging.error(f"Error getting seller with stats: {e}", exc_info=True)
        return None, {}


async def notify_seller(bot, chat_id: int, message: str) -> bool:
    """
    Helper function to notify a seller

    Args:
        bot: Bot instance
        chat_id: Seller's chat ID
        message: Message to send

    Returns:
        True if notification was sent, False otherwise
    """
    try:
        await bot.send_message(chat_id=chat_id, text=message)
        return True
    except Exception as e:
        logging.error(f"Failed to notify seller with chat_id {chat_id}: {e}")
        return False


@sellers_router.callback_query(F.data == "sellers")
async def show_sellers_list(callback: CallbackQuery, repo: RequestsRepo):
    """Handle sellers list display."""
    try:
        # Get paginated sellers and total count
        sellers, total_count = await repo.sellers.get_paginated_sellers(
            page=1, per_page=SELLERS_PER_PAGE
        )

        # Calculate total pages
        total_pages = (total_count + SELLERS_PER_PAGE - 1) // SELLERS_PER_PAGE

        # Create message text
        text = (
            f"📋 لیست فروشندگان:\n\n"
            f"🔢 تعداد کل: {convert_english_digits_to_farsi(total_count)}\n\n"
            "برای مدیریت هر فروشنده روی نام آن کلیک کنید:"
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=create_sellers_keyboard(
                sellers, page=1, total_pages=total_pages
            ),
        )
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in show_sellers_list: {e}", exc_info=True)
        await callback.answer(
            "❌ خطا در نمایش لیست فروشندگان. لطفاً دوباره تلاش کنید.", show_alert=True
        )


@sellers_router.callback_query(F.data.startswith("sellers:"))
async def handle_sellers_pagination(callback: CallbackQuery, repo: RequestsRepo):
    """Handle sellers pagination."""
    try:
        page = int(callback.data.split(":")[1])

        # Get paginated sellers and total count
        sellers, total_count = await repo.sellers.get_paginated_sellers(
            page=page, per_page=SELLERS_PER_PAGE
        )

        # Calculate total pages
        total_pages = (total_count + SELLERS_PER_PAGE - 1) // SELLERS_PER_PAGE

        # Update message with new page
        text = (
            f"📋 لیست فروشندگان:\n\n"
            f"🔢 تعداد کل: {convert_english_digits_to_farsi(total_count)}\n\n"
            "برای مدیریت هر فروشنده روی نام آن کلیک کنید:"
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=create_sellers_keyboard(sellers, page, total_pages),
        )
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in handle_sellers_pagination: {e}", exc_info=True)
        await callback.answer(
            "❌ خطا در تغییر صفحه. لطفاً دوباره تلاش کنید.", show_alert=True
        )


@sellers_router.callback_query(F.data.startswith("seller_view_"))
async def show_seller_details(callback: CallbackQuery, repo: RequestsRepo):
    """Handle seller details view."""
    try:
        seller_id = int(callback.data.removeprefix("seller_view_"))

        # Get seller with service stats
        seller, service_stats = await get_seller_with_stats(repo, seller_id)

        if not seller:
            await callback.answer("❌ فروشنده مورد نظر یافت نشد.", show_alert=True)
            return

        # Format text using helper function
        text = format_seller_details_text(seller, service_stats)

        await callback.message.edit_text(
            text=text,
            reply_markup=create_seller_detail_keyboard(seller),
        )
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in show_seller_details: {e}", exc_info=True)
        await callback.answer(
            "❌ خطا در نمایش جزئیات فروشنده. لطفاً دوباره تلاش کنید.", show_alert=True
        )


@sellers_router.callback_query(F.data.startswith("seller_suspend_"))
async def suspend_seller(callback: CallbackQuery, repo: RequestsRepo):
    """Handle seller suspension."""
    try:
        seller_id = int(callback.data.removeprefix("seller_suspend_"))

        # Update seller status
        seller = await repo.sellers.update_seller_status(
            seller_id=seller_id, status=SellerStatus.SUSPENDED, is_active=False
        )

        if not seller:
            await callback.answer("❌ فروشنده مورد نظر یافت نشد.", show_alert=True)
            return

        # Get service stats
        _, service_stats = await get_seller_with_stats(repo, seller_id)

        # Notify the seller
        await notify_seller(
            callback.bot,
            seller.chat_id,
            "⚠️ حساب کاربری شما به حالت تعلیق درآمده است. لطفاً با پشتیبانی تماس بگیرید.",
        )

        # Update admin message using helper function
        text = format_seller_details_text(seller, service_stats)

        await callback.message.edit_text(
            text=text, reply_markup=create_seller_detail_keyboard(seller)
        )

        await callback.answer("✅ فروشنده با موفقیت تعلیق شد.", show_alert=True)

    except Exception as e:
        logging.error(f"Error in suspend_seller: {e}", exc_info=True)
        await callback.answer("❌ خطا در تعلیق فروشنده.", show_alert=True)


@sellers_router.callback_query(F.data.startswith("seller_activate_"))
async def activate_seller(callback: CallbackQuery, repo: RequestsRepo):
    """Handle seller activation."""
    try:
        seller_id = int(callback.data.removeprefix("seller_activate_"))

        # Update seller status
        seller = await repo.sellers.update_seller_status(
            seller_id=seller_id, status=SellerStatus.APPROVED, is_active=True
        )

        if not seller:
            await callback.answer("❌ فروشنده مورد نظر یافت نشد.", show_alert=True)
            return

        # Get service stats
        _, service_stats = await get_seller_with_stats(repo, seller_id)

        # Notify the seller
        await notify_seller(
            callback.bot, seller.chat_id, "✅ حساب کاربری شما فعال شده است."
        )

        # Update admin message using helper function
        text = format_seller_details_text(seller, service_stats)

        await callback.message.edit_text(
            text=text, reply_markup=create_seller_detail_keyboard(seller)
        )

        await callback.answer("✅ فروشنده با موفقیت فعال شد.", show_alert=True)

    except Exception as e:
        logging.error(f"Error in activate_seller: {e}", exc_info=True)
        await callback.answer("❌ خطا در فعال‌سازی فروشنده.", show_alert=True)


@sellers_router.callback_query(F.data.startswith("seller_ban_"))
async def ban_seller(callback: CallbackQuery, repo: RequestsRepo):
    """Handle seller banning."""
    try:
        seller_id = int(callback.data.removeprefix("seller_ban_"))

        # Update seller status
        seller = await repo.sellers.update_seller_status(
            seller_id=seller_id, status=SellerStatus.BANNED, is_active=False
        )

        if not seller:
            await callback.answer("❌ فروشنده مورد نظر یافت نشد.", show_alert=True)
            return

        # Get service stats
        _, service_stats = await get_seller_with_stats(repo, seller_id)

        # Notify the seller
        await notify_seller(
            callback.bot,
            seller.chat_id,
            "🚫 حساب کاربری شما مسدود شده است. لطفاً با پشتیبانی تماس بگیرید.",
        )

        # Update admin message using helper function
        text = format_seller_details_text(seller, service_stats)

        await callback.message.edit_text(
            text=text, reply_markup=create_seller_detail_keyboard(seller)
        )

        await callback.answer("✅ فروشنده با موفقیت مسدود شد.", show_alert=True)

    except Exception as e:
        logging.error(f"Error in ban_seller: {e}", exc_info=True)
        await callback.answer("❌ خطا در مسدودسازی فروشنده.", show_alert=True)


@sellers_router.callback_query(F.data.startswith("seller_unban_"))
async def unban_seller(callback: CallbackQuery, repo: RequestsRepo):
    """Handle seller unbanning."""
    try:
        seller_id = int(callback.data.removeprefix("seller_unban_"))

        # Update seller status
        seller = await repo.sellers.update_seller_status(
            seller_id=seller_id, status=SellerStatus.APPROVED, is_active=True
        )

        if not seller:
            await callback.answer("❌ فروشنده مورد نظر یافت نشد.", show_alert=True)
            return

        # Get service stats
        _, service_stats = await get_seller_with_stats(repo, seller_id)

        # Notify the seller
        await notify_seller(
            callback.bot, seller.chat_id, "✅ حساب کاربری شما رفع مسدودیت شده است."
        )

        # Update admin message using helper function
        text = format_seller_details_text(seller, service_stats)

        await callback.message.edit_text(
            text=text, reply_markup=create_seller_detail_keyboard(seller)
        )

        await callback.answer("✅ فروشنده با موفقیت رفع مسدودیت شد.", show_alert=True)

    except Exception as e:
        logging.error(f"Error in unban_seller: {e}", exc_info=True)
        await callback.answer("❌ خطا در رفع مسدودیت فروشنده.", show_alert=True)


@sellers_router.callback_query(F.data.startswith("seller_discount_"))
async def start_edit_discount(callback: CallbackQuery, state: FSMContext):
    """Start process of editing seller discount."""
    try:
        seller_id = int(callback.data.removeprefix("seller_discount_"))

        # Store seller_id in state
        await state.update_data(seller_id=seller_id)

        # Ask for new discount
        await callback.message.edit_text(
            "📊 لطفاً درصد تخفیف جدید را وارد کنید:\n" "مثال: 15.5", reply_markup=None
        )

        # Set state
        await state.set_state(SellerManagementState.waiting_for_discount)
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in start_edit_discount: {e}", exc_info=True)
        await callback.answer(
            "❌ خطا در شروع فرآیند تغییر درصد تخفیف.", show_alert=True
        )


@sellers_router.message(SellerManagementState.waiting_for_discount)
async def process_discount_input(
    message: Message, state: FSMContext, repo: RequestsRepo
):
    """Process discount input and update seller."""
    try:
        # Parse discount
        try:
            discount = Decimal(message.text)
            if not 0 <= discount <= 100:
                await message.answer(
                    "❌ درصد تخفیف باید بین 0 تا 100 باشد. لطفاً مجدداً وارد کنید:"
                )
                return
        except InvalidOperation:
            await message.answer("❌ لطفاً یک عدد معتبر وارد کنید:")
            return

        # Get seller_id from state
        data = await state.get_data()
        seller_id = data.get("seller_id")

        if not seller_id:
            await message.answer("❌ خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.")
            await state.clear()
            return

        # Update seller discount
        seller = await repo.sellers.update_seller_discount_and_debt_limit(
            seller_id=seller_id, discount_percent=discount
        )

        if not seller:
            await message.answer("❌ فروشنده مورد نظر یافت نشد.")
            await state.clear()
            return

        # Get service stats
        _, service_stats = await get_seller_with_stats(repo, seller_id)

        # Notify the seller
        await notify_seller(
            message.bot,
            seller.chat_id,
            f"📊 درصد تخفیف شما به {convert_english_digits_to_farsi(discount)}% تغییر یافت.",
        )

        # Clear state
        await state.clear()

        # Show updated seller details using helper function
        text = format_seller_details_text(seller, service_stats)

        # Send updated seller details
        await message.answer(
            text=text, reply_markup=create_seller_detail_keyboard(seller)
        )

    except Exception as e:
        logging.error(f"Error in process_discount_input: {e}", exc_info=True)
        await message.answer("❌ خطا در تغییر درصد تخفیف. لطفاً دوباره تلاش کنید.")
        await state.clear()


@sellers_router.callback_query(F.data.startswith("seller_debt_"))
async def start_edit_debt_limit(callback: CallbackQuery, state: FSMContext):
    """Start process of editing seller debt limit."""
    try:
        seller_id = int(callback.data.removeprefix("seller_debt_"))

        # Store seller_id in state
        await state.update_data(seller_id=seller_id)

        # Ask for new debt limit
        await callback.message.edit_text(
            "💰 لطفاً محدودیت بدهی جدید را به تومان وارد کنید:\n" "مثال: 1000000",
            reply_markup=None,
        )

        # Set state
        await state.set_state(SellerManagementState.waiting_for_debt_limit)
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in start_edit_debt_limit: {e}", exc_info=True)
        await callback.answer(
            "❌ خطا در شروع فرآیند تغییر محدودیت بدهی.", show_alert=True
        )


@sellers_router.message(SellerManagementState.waiting_for_debt_limit)
async def process_debt_limit_input(
    message: Message, state: FSMContext, repo: RequestsRepo
):
    """Process debt limit input and update seller."""
    try:
        # Parse debt limit
        try:
            debt_limit = Decimal(message.text)
            if debt_limit < 0:
                await message.answer(
                    "❌ محدودیت بدهی نمی‌تواند منفی باشد. لطفاً مجدداً وارد کنید:"
                )
                return
        except InvalidOperation:
            await message.answer("❌ لطفاً یک عدد معتبر وارد کنید:")
            return

        # Get seller_id from state
        data = await state.get_data()
        seller_id = data.get("seller_id")

        if not seller_id:
            await message.answer("❌ خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.")
            await state.clear()
            return

        # Update seller debt limit
        seller = await repo.sellers.update_seller_discount_and_debt_limit(
            seller_id=seller_id, debt_limit=debt_limit
        )

        if not seller:
            await message.answer("❌ فروشنده مورد نظر یافت نشد.")
            await state.clear()
            return

        # Get service stats
        _, service_stats = await get_seller_with_stats(repo, seller_id)

        # Notify the seller
        await notify_seller(
            message.bot,
            seller.chat_id,
            f"💰 محدودیت بدهی شما به {format_currency(debt_limit, convert_to_farsi=True)} تومان تغییر یافت.",
        )

        # Clear state
        await state.clear()

        # Show updated seller details using helper function
        text = format_seller_details_text(seller, service_stats)

        # Send updated seller details
        await message.answer(
            text=text, reply_markup=create_seller_detail_keyboard(seller)
        )

    except Exception as e:
        logging.error(f"Error in process_debt_limit_input: {e}", exc_info=True)
        await message.answer("❌ خطا در تغییر محدودیت بدهی. لطفاً دوباره تلاش کنید.")
        await state.clear()


@sellers_router.callback_query(F.data.startswith("seller_services_"))
async def show_seller_services(callback: CallbackQuery, repo: RequestsRepo):
    """Show services for a specific seller."""
    await callback.answer("این قسمت توسعه داده نشده است.", show_alert=True)

    # try:
    #     seller_id = int(callback.data.removeprefix("seller_services_"))
    #
    #     # Get seller
    #     seller = await repo.sellers.get_seller_by_id(seller_id)
    #
    #     if not seller:
    #         await callback.answer("❌ فروشنده مورد نظر یافت نشد.", show_alert=True)
    #         return
    #
    #     # Get services for this seller (first page)
    #     services, total_count = await repo.services.get_seller_services(
    #         seller_id=seller_id, page=1, per_page=5
    #     )
    #
    #     if not services:
    #         await callback.answer("این فروشنده هیچ سرویسی ندارد.", show_alert=True)
    #         return
    #
    #     # Create services list text
    #     text = f"📋 لیست سرویس‌های فروشنده {seller.username or seller.full_name}:\n\n"
    #
    #     for i, service in enumerate(services, 1):
    #         status_emoji = {
    #             ServiceStatus.UNUSED: "⚪",
    #             ServiceStatus.INACTIVE: "🔴",
    #             ServiceStatus.ACTIVE: "🟢",
    #             ServiceStatus.EXPIRED: "🟡",
    #             ServiceStatus.DELETED: "⚫",
    #         }.get(service.status, "❓")
    #
    #         text += (
    #             f"{i}. {status_emoji} {service.peer.public_id if service.peer else 'N/A'}\n"
    #             f"   💰 قیمت: {format_currency(service.seller_price, convert_to_farsi=True)} تومان\n\n"
    #         )
    #
    #     # Create keyboard to go back to seller details
    #     kb = InlineKeyboardBuilder()
    #     kb.button(
    #         text="🔙 بازگشت به اطلاعات فروشنده",
    #         callback_data=f"seller_view_{seller_id}",
    #     )
    #     kb.adjust(1)
    #
    #     await callback.message.edit_text(text=text, reply_markup=kb.as_markup())
    #     await callback.answer()
    #
    # except Exception as e:
    #     logging.error(f"Error in show_seller_services: {e}", exc_info=True)
    #     await callback.answer("❌ خطا در نمایش سرویس‌های فروشنده.", show_alert=True)


@sellers_router.callback_query(F.data == "sellers_search")
async def start_seller_search(callback: CallbackQuery, state: FSMContext):
    """Start seller search process."""
    try:
        await callback.answer("این قسمت توسعه داده نشده است.", show_alert=True)
        # await callback.message.edit_text(
        #     "🔍 لطفاً نام کاربری یا نام فروشنده مورد نظر را وارد کنید:",
        #     reply_markup=None,
        # )
        #
        # # Set state
        # await state.set_state(SellerManagementState.waiting_for_search_query)
        # await callback.answer()

    except Exception as e:
        logging.error(f"Error in start_seller_search: {e}", exc_info=True)
        await callback.answer("❌ خطا در شروع فرآیند جستجو.", show_alert=True)


@sellers_router.message(SellerManagementState.waiting_for_search_query)
async def process_seller_search(
    message: Message, state: FSMContext, repo: RequestsRepo
):
    """Process seller search query."""
    try:
        search_query = message.text.strip()

        if not search_query:
            await message.answer("❌ لطفاً یک عبارت جستجو وارد کنید.")
            return

        # Search for sellers
        sellers = await repo.sellers.search_sellers(search_query)

        if not sellers:
            # Create keyboard to go back to sellers list
            kb = InlineKeyboardBuilder()
            kb.button(text="🔙 بازگشت به لیست فروشندگان", callback_data="sellers")
            kb.adjust(1)

            await message.answer(
                "❌ هیچ فروشنده‌ای با این مشخصات یافت نشد.", reply_markup=kb.as_markup()
            )
            await state.clear()
            return

        # Clear state
        await state.clear()

        # Create message text
        text = (
            f'🔍 نتایج جستجو برای "{search_query}":\n\n'
            f"🔢 تعداد نتایج: {convert_english_digits_to_farsi(len(sellers))}\n\n"
            "برای مدیریت هر فروشنده روی نام آن کلیک کنید:"
        )

        # Create keyboard
        await message.answer(
            text=text,
            reply_markup=create_sellers_keyboard(sellers, page=1, total_pages=1),
        )

    except Exception as e:
        logging.error(f"Error in process_seller_search: {e}", exc_info=True)
        await message.answer("❌ خطا در جستجوی فروشنده. لطفاً دوباره تلاش کنید.")
        await state.clear()


@sellers_router.callback_query(F.data == "seller_disable_services")
async def start_seller_search(callback: CallbackQuery, state: FSMContext):
    """Start seller search process."""
    await callback.answer("این قسمت توسعه داده نشده است.", show_alert=True)


@sellers_router.callback_query(F.data == "seller_enable_services")
async def start_seller_search(callback: CallbackQuery, state: FSMContext):
    """Start seller search process."""

    await callback.answer("این قسمت توسعه داده نشده است.", show_alert=True)


@sellers_router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """Handle ignore callback - just answer to remove loading state"""
    await callback.answer()
