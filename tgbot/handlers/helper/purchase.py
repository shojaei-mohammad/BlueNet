# tgbot/handlers/helper/purchase.py
import asyncio
import logging
from asyncio import CancelledError
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

from aiogram import html
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from aiogram.types import CallbackQuery

from infrastructure.database.models import Seller, ServiceType, Service
from infrastructure.database.repo.requests import RequestsRepo
from infrastructure.services.purchase import PurchaseService
from tgbot.services.utils import convert_to_shamsi, format_currency


async def notify_admins(
    bot, admin_ids: list[int], service: Service, seller: Seller, public_id: str
) -> None:
    """
    Notify administrators about a new service purchase.

    Args:
        public_id:
        bot: Telegram bot instance
        admin_ids: List of admin Telegram IDs
        service: Service instance containing purchase details
        seller: Seller instance who made the purchase
    """
    try:
        admin_message = (
            f"🔔 سرویس جدید خریداری شد\n\n"
            f"👤 {html.bold('فروشنده:')} {seller.username} (کد: {seller.id})\n"
            f"💸 {html.bold('بدهی:')} {format_currency(seller.current_debt, convert_to_farsi=True)} تومان \n"
            f"📊 {html.bold('درصد تخفیف:')} {seller.discount_percent}%\n"
            f"🏷 {html.bold('شناسه سرویس:')} {html.code(service.id)}\n"
            f"🔧 {html.bold('شناسه کانفیگ:')} {public_id}\n"
            f"💰 {html.bold('تعرفه:')} {service.tariff.description}\n"
            f"💵 {html.bold('قیمت فروشنده:')} {format_currency(service.seller_price, convert_to_farsi=True)} تومان \n"
            f"💲 {html.bold('قیمت اصلی:')} {format_currency(service.original_price, convert_to_farsi=True)} تومان \n"
            f"📅 {html.bold('تاریخ:')} {convert_to_shamsi(service.created_at)}\n"
            f"🚦 {html.bold('وضعیت:')} {service.status.value}"
        )

        logging.info(
            f"Sending purchase notification to {len(admin_ids)} admins for service {service.id}"
        )

        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, admin_message, parse_mode="HTML")
                logging.debug(
                    f"Successfully notified admin {admin_id} about service {service.id}"
                )
            except Exception as e:
                logging.error(
                    f"Failed to notify admin {admin_id}: {str(e)}", exc_info=True
                )

    except Exception as e:
        logging.error(f"Error in notify_admins: {str(e)}", exc_info=True)


async def handle_purchase(
    callback: CallbackQuery,
    repo: RequestsRepo,
    admin_ids: list[int],
    seller: Seller,
) -> None:
    """
    Handle the purchase process for a service.

    Args:
        callback: Telegram callback query
        repo: Repository instance for database operations
        admin_ids: List of admin Telegram IDs
        seller: Seller instance making the purchase
    """
    logging.info(f"Starting purchase process for seller {seller.id}")

    try:
        # Extract and validate tariff ID
        try:
            tariff_id = UUID(callback.data.split("_")[1])
            logging.debug(f"Processing purchase for tariff {tariff_id}")
        except (ValueError, IndexError) as e:
            logging.error(f"Invalid tariff ID format: {str(e)}")
            await callback.answer("فرمت شناسه تعرفه نامعتبر است.", show_alert=True)
            return

        # Get tariff details
        tariff = await repo.tariffs.get_tariff_details(tariff_id)
        if not tariff:
            logging.warning(f"Tariff {tariff_id} not found")
            await callback.answer("تعرفه مورد نظر یافت نشد.", show_alert=True)
            return

        # Check debt limit
        total_cost = tariff.price * (1 - seller.discount_percent / 100)
        if seller.current_debt + total_cost > seller.debt_limit:
            logging.warning(
                f"Debt limit exceeded for seller {seller.id}. "
                f"Current: {seller.current_debt}, New: {total_cost}, Limit: {seller.debt_limit}"
            )
            await callback.answer(
                "این خرید باعث می‌شود بدهی شما از سقف مجاز فراتر رود. لطفاً بدهی خود را تسویه کنید.",
                show_alert=True,
            )
            return

        # Find suitable interface
        interface = await repo.interfaces.get_available_interface(
            service_type=tariff.service_type,
            country_code=(
                tariff.country_code
                if tariff.service_type == ServiceType.FIXED
                else None
            ),
        )

        if not interface:
            logging.warning(
                f"No available interface found for service type {tariff.service_type}"
            )
            await callback.answer(
                "در حال حاضر سرور مناسب در دسترس نیست. لطفاً بعداً تلاش کنید.",
                show_alert=True,
            )
            return

        # Process purchase
        logging.info(
            f"Processing purchase for seller {seller.id} with tariff {tariff_id}"
        )
        purchase_service = PurchaseService(repo)
        service, qr_code, config_document, public_id = (
            await purchase_service.process_purchase(
                seller=seller, tariff=tariff, interface=interface
            )
        )

        # Notify admins
        await notify_admins(callback.message.bot, admin_ids, service, seller, public_id)

        # Send confirmation message and files
        await callback.message.answer(
            f"خرید شما با موفقیت انجام شد!\n"
            f"شناسه سرویس: {service.id}\n"
            f"تعرفه: {tariff.description}\n"
            f"مبلغ: {service.seller_price:,} تومان\n"
            f"مدت: {tariff.duration_days} روز"
        )

        await callback.message.answer_photo(photo=qr_code, caption="کانفیگ VPN شما")

        await callback.message.answer_document(
            document=config_document, caption="فایل کانفیگ VPN"
        )

        logging.info(
            f"Successfully completed purchase process for service {service.id}"
        )

    except ValueError as e:
        logging.error(f"Validation error in purchase: {str(e)}", exc_info=True)
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logging.error(f"Error processing purchase: {str(e)}", exc_info=True)
        await callback.answer(
            "خطا در پردازش خرید. لطفاً دوباره تلاش کنید.", show_alert=True
        )


@asynccontextmanager
async def show_loading_status(
    message, initial_text: str = "⏳ در حال پردازش..."
) -> AsyncGenerator:
    """
    Context manager to show loading status while processing a request.

    Args:
        message: The message object to respond to
        initial_text: The initial loading message to show

    Raises:
        TelegramAPIError: If there's an API error when sending messages
        ValueError: If the message parameters are invalid
    """
    loading_message = None
    task = None
    logger = logging.getLogger(__name__)

    async def update_chat_action():
        while True:
            try:
                await message.bot.send_chat_action(
                    chat_id=message.chat.id, action="typing"
                )
                await asyncio.sleep(4)  # Send new action every 4 seconds
            except TelegramBadRequest as e:
                logger.warning(f"Bad request while sending chat action: {e}")
                break
            except TelegramAPIError as e:
                logger.error(f"Telegram API error while sending chat action: {e}")
                break
            except CancelledError:
                # Normal cancellation, no need to log
                break
            except Exception as e:
                logger.error(
                    f"Unexpected error in chat action loop: {e}", exc_info=True
                )
                break

    try:
        # Show initial loading message
        loading_message = await message.answer(initial_text)

        # Start continuous chat action
        task = asyncio.create_task(update_chat_action())
        yield

    finally:
        # Clean up task
        if task and not task.done():
            task.cancel()
            try:
                await task
            except CancelledError:
                pass  # Task cancellation is expected
            except Exception as e:
                logger.error(
                    f"Error while cancelling chat action task: {e}", exc_info=True
                )

        # Clean up loading message
        if loading_message:
            try:
                await loading_message.delete()
            except TelegramBadRequest as e:
                logger.warning(
                    f"Could not delete loading message (might be already deleted): {e}"
                )
            except TelegramAPIError as e:
                logger.error(f"Telegram API error while deleting loading message: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error while deleting loading message: {e}",
                    exc_info=True,
                )


# Modified handle_bulk_purchase function
async def handle_bulk_purchase(
    callback: CallbackQuery,
    repo: RequestsRepo,
    admin_ids: list[int],
    seller: Seller,
    quantity: int,
) -> None:
    """Handle bulk purchase of multiple dynamic IPs with rate limiting"""

    # Answer callback immediately to prevent timeout
    await callback.answer("⏳ در حال پردازش درخواست شما...")

    async with show_loading_status(callback.message, "⏳ در حال ایجاد سرویس‌ها..."):
        try:
            tariff_id = UUID(callback.data.split("_")[1])
            tariff = await repo.tariffs.get_tariff_details(tariff_id)

            if not tariff:
                await callback.message.answer("تعرفه مورد نظر یافت نشد.")
                return

            # Calculate total cost
            total_cost = tariff.price * quantity * (1 - seller.discount_percent / 100)

            if seller.current_debt + total_cost > seller.debt_limit:
                await callback.message.answer(
                    "این خرید باعث می‌شود بدهی شما از سقف مجاز فراتر رود. لطفاً بدهی خود را تسویه کنید."
                )
                return

            # Find suitable interface
            interface = await repo.interfaces.get_available_interface(
                service_type=tariff.service_type,
                country_code=None,
            )

            if not interface:
                await callback.message.answer(
                    "در حال حاضر سرور مناسب با ظرفیت کافی در دسترس نیست."
                )
                return

            # Process multiple purchases with rate limiting
            purchase_service = PurchaseService(repo)
            configs = []
            services = []
            failed_count = 0
            max_retries = 3  # Maximum retry attempts per purchase
            delay_between_purchases = 1.0  # 1 second between purchases
            delay_between_configs = 0.5  # 0.5 seconds between sending configs

            for i in range(quantity):
                # Update loading message with progress
                await callback.message.edit_text(
                    f"⏳ در حال ایجاد سرویس {i + 1} از {quantity}..."
                )

                # Attempt purchase with retries
                for attempt in range(max_retries):
                    try:
                        # Add delay between purchases
                        if i > 0:
                            await asyncio.sleep(delay_between_purchases)

                        service, qr_code, config_document, public_id = (
                            await purchase_service.process_purchase(
                                seller=seller, tariff=tariff, interface=interface
                            )
                        )
                        configs.append((qr_code, config_document))
                        services.append((service, public_id))
                        break  # Success, exit retry loop
                    except Exception as e:
                        if attempt == max_retries - 1:  # Last attempt failed
                            failed_count += 1
                            logging.error(
                                f"Failed to create service {i + 1} after {max_retries} attempts: {str(e)}",
                                exc_info=True,
                            )
                        else:
                            await asyncio.sleep(1)  # Wait before retry

            # Send confirmation
            success_count = quantity - failed_count
            await callback.message.answer(
                f"✅ خرید {quantity} سرویس انجام شد!\n"
                f"موفق: {success_count}, ناموفق: {failed_count}\n"
                f"تعرفه: {tariff.description}\n"
                f"مبلغ کل: {format_currency(total_cost, convert_to_farsi=True)} تومان\n"
                f"مدت: {tariff.duration_days} روز"
            )

            # Send configs with rate limiting
            for i, (qr_code, config_document) in enumerate(configs, 1):
                try:
                    await callback.message.answer(
                        f"🔹 ارسال کانفیگ {i} از {success_count}:"
                    )
                    await callback.message.answer_photo(
                        photo=qr_code,
                        caption=f"کد QR کانفیگ {i}: {services[i - 1][1]}",  # Get public_id from services list
                    )
                    await callback.message.answer_document(
                        document=config_document,
                        caption=f"فایل کانفیگ {i}: {services[i - 1][1]}",
                    )

                    # Add delay between sending configs
                    if i < len(configs):  # No delay after last config
                        await asyncio.sleep(delay_between_configs)

                except Exception as e:
                    logging.error(f"Failed to send config {i}: {str(e)}", exc_info=True)

            # Notify admins with rate limiting
            for i, (service, public_id) in enumerate(services, 1):
                try:
                    await notify_admins(
                        callback.message.bot, admin_ids, service, seller, public_id
                    )
                    # Add small delay between admin notifications
                    if i < len(services):
                        await asyncio.sleep(0.3)
                except Exception as e:
                    logging.error(
                        f"Failed to notify admins for service {i}: {str(e)}",
                        exc_info=True,
                    )

        except Exception as e:
            logging.error(f"Error processing bulk purchase: {str(e)}", exc_info=True)
            await callback.message.answer(
                "❌ خطا در پردازش خرید. لطفاً دوباره تلاش کنید."
            )
