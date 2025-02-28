# tgbot/handlers/admin.py
import logging
from decimal import InvalidOperation, Decimal
from uuid import UUID

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models.sellers import UserRole, Seller, SellerStatus
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.admin import AdminFilter
from tgbot.keyboards.menu import create_markup, menu_structure
from tgbot.services.back_button import add_return_buttons
from tgbot.services.utils import format_currency, broadcast_messages
from tgbot.states.admin import SellerRegistration, InputCustomMessage

admin_router = Router()
admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())


async def _process_menu_navigation(callback: CallbackQuery, menu_type: str) -> None:
    """Handle menu navigation updates."""
    try:
        markup, menu_text = await create_markup(menu_type, UserRole.ADMIN)
        await callback.message.edit_text(text=menu_text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            await callback.answer()
        else:
            raise


@admin_router.message(CommandStart())
async def admin_start(
    message: Message,
    seller: Seller,
):
    """
    Handle /start command for admin users
    Additional check for admin role in database
    """
    if not seller or seller.user_role != UserRole.ADMIN:
        logging.info(
            f"Admin with chat_id {seller.chat_id} and user_role {seller.user_role} is not admin"
        )
        return

    markup, text = await create_markup("admins_main_menu", seller.user_role)
    await message.answer(text=text, reply_markup=markup)


@admin_router.message(SellerRegistration.SET_DISCOUNT)
async def handle_discount_input(message: Message, state: FSMContext):
    """Handle discount percentage input"""
    try:
        discount = Decimal(message.text)
        if not 0 <= discount <= 100:
            await message.answer(
                "❌ درصد تخفیف باید بین 0 تا 100 باشد. لطفاً مجدداً وارد کنید:"
            )
            return

        # Store raw Decimal value in state
        await state.update_data(discount=str(discount))

        # Ask for debt limit
        await message.answer(
            "💰 لطفاً محدودیت بدهی فروشنده را به تومان وارد کنید:\n" "مثال: 1000000"
        )
        await state.set_state(SellerRegistration.SET_DEBT_LIMIT)

    except InvalidOperation:
        await message.answer("❌ لطفاً یک عدد معتبر وارد کنید:")


@admin_router.message(SellerRegistration.SET_DEBT_LIMIT)
async def handle_debt_limit_input(message: Message, state: FSMContext):
    """Handle debt limit input and complete registration"""
    try:
        debt_limit = Decimal(message.text)
        if debt_limit < 0:
            await message.answer(
                "❌ محدودیت بدهی نمی‌تواند منفی باشد. لطفاً مجدداً وارد کنید:"
            )
            return

        # Get stored data (raw Decimal values)
        data = await state.get_data()
        discount = data["discount"]

        # Create confirmation keyboard
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ تایید", callback_data="confirm_registration")
        kb.button(text="❌ لغو", callback_data="cancel_registration")
        kb.adjust(2)

        # Show confirmation message
        await message.answer(
            "📋 لطفاً اطلاعات زیر را تایید کنید:\n\n"
            f"درصد تخفیف: {discount}%\n"
            f"محدودیت بدهی: {format_currency(debt_limit, convert_to_farsi=True)} تومان\n",
            reply_markup=kb.as_markup(),
        )

        # Store raw Decimal value in state
        await state.update_data(debt_limit=str(debt_limit))
        await state.set_state(SellerRegistration.CONFIRM_DETAILS)

    except InvalidOperation:
        await message.answer("❌ لطفاً یک عدد معتبر وارد کنید:")


@admin_router.callback_query(
    SellerRegistration.CONFIRM_DETAILS, F.data == "confirm_registration"
)
async def handle_registration_confirmation(
    callback: CallbackQuery, state: FSMContext, repo: RequestsRepo
):
    """Handle final confirmation and complete registration"""
    try:
        # Get stored data (raw Decimal values)
        data = await state.get_data()
        seller_id = data["seller_id"]
        discount = Decimal(data["discount"])
        debt_limit = Decimal(data["debt_limit"])
        formatted_dept_limit = format_currency(debt_limit, convert_to_farsi=True)

        # Update seller in database
        seller = await repo.sellers.complete_seller_registration(
            seller_id=seller_id,
            discount_percent=discount,
            debt_limit=debt_limit,
            status=SellerStatus.APPROVED,
        )

        # Notify the seller
        await callback.bot.send_message(
            chat_id=seller.chat_id,
            text=(
                "🎉 تبریک! درخواست شما تایید شد.\n\n"
                f"درصد تخفیف شما: {discount}%\n"
                f"سقف بدهی: {formatted_dept_limit} تومان\n\n"
                "\nاکنون می‌توانید از ربات استفاده کنید."
                "/start"
            ),
        )

        # Confirm to admin
        await callback.message.edit_text(
            f"✅ فروشنده با موفقیت ثبت شد!\n\n"
            f"شناسه: {seller_id}\n"
            f"درصد تخفیف: {discount}%\n"
            f"محدودیت بدهی: {formatted_dept_limit} تومان"
        )

    except Exception as e:
        logging.error(f"Error completing registration: {e}")
        await callback.message.edit_text("❌ خطا در ثبت اطلاعات. لطفا مجددا تلاش کنید.")

    finally:
        await state.clear()


@admin_router.callback_query(
    SellerRegistration.CONFIRM_DETAILS, F.data == "cancel_registration"
)
async def handle_registration_cancellation(callback: CallbackQuery, state: FSMContext):
    """Handle registration cancellation"""
    await callback.message.edit_text("❌ فرآیند ثبت نام لغو شد.")
    await state.clear()


@admin_router.message(InputCustomMessage.wait_for_message)
async def broadcast_handler(message: Message, state: FSMContext):
    try:
        input_text = message.text
        await message.delete()

        confirm_text = (
            "درصورت تایید با فشردن دکمه ارسال پیام شما ارسال خواهد شد.\n"
            "در صورت نیاز به ویرایش فقط کافیست متن ویرایش شده رو دوباره ارسال کنید."
        )
        confirm_text += "➖" * 17
        confirm_text += "\n\n" + input_text

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📨 ارسال", callback_data="SendMessage:confirm"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ لغو", callback_data="SendMessage:reject"
                    )
                ],
            ]
        )

        # Get existing menu message IDs
        data = await state.get_data()
        message_ids = data.get("menu_message_ids", [])

        # Delete previous menu messages
        for msg_id in message_ids:
            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id, message_id=msg_id
                )
            except Exception as e:
                logging.error(f"Failed to delete menu message {msg_id}: {e}")

        # Send new menu message
        sent_message = await message.answer(text=confirm_text, reply_markup=markup)

        # Update menu message IDs in state
        message_ids = [sent_message.message_id]
        await state.update_data(menu_message_ids=message_ids, admin_msg=input_text)

        logging.info(f"Admin {message.from_user.id} prepared broadcast message")
    except Exception as e:
        logging.error(f"Error in broadcast_handler: {e}")
        await message.answer(
            "An error occurred while processing your message. Please try again."
        )


@admin_router.callback_query()
async def default_admin_callback_query(
    callback: CallbackQuery, state: FSMContext, repo: RequestsRepo
):
    """
    Asynchronous handler for callback queries triggered by inline keyboard buttons.
    """
    try:

        callback_data = callback.data
        chat_id = callback.message.chat.id

        logging.debug(f"Received callback: {callback_data} from user {chat_id}")

        if callback_data in menu_structure:
            await _process_menu_navigation(callback, callback_data)
        elif callback_data.startswith("confirm_seller_"):
            await callback.answer()
            seller_id = int(callback_data.split("_")[2])
            print(seller_id)
            # Store seller_id in state
            await state.update_data(seller_id=seller_id)

            # Ask for discount percentage
            await callback.message.edit_text(
                "📊 لطفاً درصد تخفیف فروشنده را وارد کنید:\n" "مثال: 15.5"
            )
            await state.set_state(SellerRegistration.SET_DISCOUNT)
        elif callback_data.startswith("reject_seller_"):

            seller_id = int(callback_data.split("_")[2])

            """Handle user rejection"""

            try:

                seller = await repo.sellers.update_seller_status(
                    seller_id=seller_id,
                    status=SellerStatus.BANNED,
                    is_active=False,
                )
                # Notify the seller

                await callback.bot.send_message(
                    chat_id=seller.chat_id, text="⛔️ متاسفانه درخواست شما تایید نشد."
                )

                await callback.message.edit_text(text="✅ درخواست با موفقیت رد شد.")

            except Exception as e:

                logging.error(f"Error rejecting user: {e}")

                await callback.message.edit_text(
                    "❌ خطا در رد درخواست. لطفا مجددا تلاش کنید."
                )
        elif callback_data.startswith("confirm_settlement_"):
            try:
                transaction_id = UUID(callback_data.removeprefix("confirm_settlement_"))

                # Get transaction details
                transaction = await repo.transactions.get_transaction(transaction_id)
                if not transaction:
                    await callback.answer("❌ تراکنش یافت نشد.", show_alert=True)
                    return

                # Get seller details
                seller = await repo.sellers.get_seller_by_id(transaction.seller_id)
                if not seller:
                    await callback.answer("❌ فروشنده یافت نشد.", show_alert=True)
                    return

                # Update seller's debt
                await repo.sellers.update_seller_dept(
                    seller_id=seller.id,
                    seller_price=-transaction.amount,  # Negative amount to reduce debt
                    profit=Decimal(0),
                )

                kb = InlineKeyboardBuilder()
                markup = add_return_buttons(kb, "users_main_menu")

                # Notify seller
                await callback.bot.send_message(
                    chat_id=seller.chat_id,
                    text=(
                        "✅ درخواست تسویه حساب شما تایید شد.\n\n"
                        f"💰 مبلغ: {format_currency(transaction.amount, convert_to_farsi=True)} تومان"
                    ),
                    reply_markup=markup,
                )

                # Update admin message
                await callback.message.edit_text(
                    callback.message.text + "\n\n✅ تایید شده", reply_markup=None
                )

                await callback.answer(
                    "✅ تسویه حساب با موفقیت تایید شد.", show_alert=True
                )

            except Exception as e:
                logging.error(f"Error in confirm_settlement: {e}")
                await callback.answer("❌ خطا در تایید تسویه حساب.", show_alert=True)
        elif callback_data.startswith("reject_settlement_"):
            try:
                transaction_id = UUID(callback_data.removeprefix("reject_settlement_"))

                # Get transaction details
                transaction = await repo.transactions.get_transaction(transaction_id)
                if not transaction:
                    await callback.answer("❌ تراکنش یافت نشد.", show_alert=True)
                    return

                # Get seller details
                seller = await repo.sellers.get_seller_by_id(transaction.seller_id)
                if not seller:
                    await callback.answer("❌ فروشنده یافت نشد.", show_alert=True)
                    return

                # Delete the transaction
                await repo.transactions.delete_transaction(transaction_id)

                # Notify seller
                await callback.bot.send_message(
                    chat_id=seller.chat_id,
                    text="❌ درخواست تسویه حساب شما رد شد. لطفا مجددا تلاش کنید.",
                )

                # Update admin message
                await callback.message.edit_text(
                    callback.message.text + "\n\n❌ رد شده", reply_markup=None
                )

                await callback.answer("❌ درخواست تسویه حساب رد شد.", show_alert=True)

            except Exception as e:
                logging.error(f"Error in reject_settlement: {e}")
                await callback.answer(
                    "❌ خطا در رد درخواست تسویه حساب.", show_alert=True
                )
        elif callback_data == "send_message":
            try:
                await state.set_state(InputCustomMessage.wait_for_message)
                msg = await callback.message.edit_text("پیام را وارد نمایید.")
                await state.set_data({"menu_message_ids": [msg.message_id]})
                logging.info(
                    f"Admin {callback.message.from_user.id} initiated broadcast message"
                )
            except Exception as e:
                logging.error(f"Error in broadcaster_handler: {e}")
                await callback.message.edit_text(
                    "An error occurred. Please try again later."
                )
        elif callback_data.startswith("SendMessage"):
            try:
                action = callback.data.split(":")[1]
                data = await state.get_data()
                message_to_broadcast = data.get("admin_msg")
                menu_message_ids = data.get("menu_message_ids", [])

                # Delete all menu messages
                for menu_message_id in menu_message_ids:
                    try:
                        await callback.bot.delete_message(
                            callback.message.chat.id, menu_message_id
                        )
                    except Exception as e:
                        logging.error(
                            f"Failed to delete menu message {menu_message_id}: {e}"
                        )

                if action == "confirm":
                    await callback.answer(
                        "Broadcasting started. Please wait for the report."
                    )
                    all_users_chat_ids = await repo.sellers.get_all_chat_ids()

                    successful, failed = await broadcast_messages(
                        callback.bot, all_users_chat_ids, message_to_broadcast
                    )

                    report = (
                        f"Broadcast completed:\nSuccessful: "
                        f"{successful}\nFailed: {failed}\nTotal: {len(all_users_chat_ids)}"
                    )
                    await callback.message.answer(report)
                    logging.info(
                        f"Admin {callback.from_user.id} completed broadcast. Success: {successful}, Failed: {failed}"
                    )
                else:
                    await callback.answer("Broadcast cancelled.")
                    logging.info(f"Admin {callback.from_user.id} cancelled broadcast")

                await state.clear()
            except Exception as e:
                logging.error(f"Error in send_broadcast: {e}")
                await callback.message.answer(
                    "An error occurred during the broadcast process. Please try again later."
                )
        else:
            logging.info(f"undefined callback: {callback_data}")
            await callback.answer(text="منو تعریف نشده است.")
    except TelegramBadRequest as e:
        logging.error(f"Telegram API error: {e}")
        await callback.answer(
            "⚠️ خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.", show_alert=True
        )
        await state.clear()
    except Exception as e:
        logging.error(f"Unexpected error in callback handler: {e}")
        await callback.answer(
            "⚠️ متأسفانه مشکلی پیش آمده. لطفاً دوباره تلاش کنید.", show_alert=True
        )
        await state.clear()
