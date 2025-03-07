# tgbot/handlers/start.py
import logging

from aiogram import Router, html
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models.sellers import Seller, SellerStatus
from tgbot.config import Config
from tgbot.keyboards.menu import create_markup

user_router = Router()


@user_router.message(CommandStart())
async def user_start_without_link(message: Message, seller: Seller, config: Config):
    """Handle /start command and different seller statuses"""

    if seller.status == SellerStatus.BANNED:
        await message.answer(
            "⛔️ " + html.bold("دسترسی مسدود شده!") + "\n\n"
            "متأسفانه دسترسی شما به ربات مسدود شده است. "
            "در صورت نیاز به بررسی مجدد، لطفاً با پشتیبانی تماس بگیرید."
        )

    elif seller.status == SellerStatus.SUSPENDED:
        kb = InlineKeyboardBuilder()
        kb.button(text="📞 تماس با پشتیبانی", url=config.tg_bot.support_link)

        await message.answer(
            "⚠️ " + html.bold("حساب کاربری معلق شده!") + "\n\n"
            "حساب کاربری شما موقتاً معلق شده است. "
            "برای اطلاعات بیشتر و رفع تعلیق با پشتیبانی تماس بگیرید.",
            reply_markup=kb.as_markup(),
        )

    elif seller.status == SellerStatus.APPROVED:
        # Show main menu for approved sellers
        markup, text = await create_markup("users_main_menu", seller.user_role)

        await message.answer(text=text, reply_markup=markup)

    elif seller.status == SellerStatus.PENDING:
        await message.answer(
            "👋 " + html.bold("سلام کاربر عزیز!") + "\n\n"
            "🔄 درخواست شما در حال بررسی است.\n"
            "📩 به محض تایید، به شما اطلاع‌رسانی خواهد شد.\n"
            "⏳ لطفاً شکیبا باشید."
        )

        # Notify admins about the pending request
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ تایید", callback_data=f"confirm_seller_{seller.id}")
        kb.button(text="❌ رد کردن", callback_data=f"reject_seller_{seller.id}")
        kb.adjust(2)

        admin_notification = (
            "📩 " + html.bold("درخواست ثبت‌نام جدید") + "\n\n"
            f"👤 شناسه کاربر: {seller.chat_id}\n"
            f"📝 نام کامل: {seller.full_name}\n"
            f"🔍 وضعیت: {SellerStatus.PENDING.value}\n\n"
            "لطفاً درخواست را بررسی کنید."
        )

        for admin_chat_id in config.tg_bot.admin_ids:
            try:
                await message.bot.send_message(
                    chat_id=admin_chat_id,
                    text=admin_notification,
                    reply_markup=kb.as_markup(),
                )
            except Exception as e:
                logging.error(f"Failed to notify admin {admin_chat_id}: {e}")

    else:  # New user or unknown status
        await message.answer(
            "⛔️ " + html.bold("دسترسی محدود") + "\n\n"
            "این ربات فقط برای فروشندگان تایید شده قابل استفاده است.\n"
            "در صورت نیاز به دسترسی، لطفاً با پشتیبانی تماس بگیرید.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📞 تماس با پشتیبانی", url=config.tg_bot.support_link
                        )
                    ]
                ]
            ),
        )
