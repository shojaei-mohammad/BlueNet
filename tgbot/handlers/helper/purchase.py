import logging
from uuid import UUID

from aiogram import html
from aiogram.types import CallbackQuery

from infrastructure.database.models import Seller, ServiceType, Service
from infrastructure.database.repo.requests import RequestsRepo
from infrastructure.services.purchase import PurchaseService
from tgbot.services.utils import convert_to_shamsi, format_currency

logger = logging.getLogger(__name__)


async def notify_admins(
    bot, admin_ids: list[int], service: Service, seller: Seller, public_id: str
) -> None:
    """
    Notify administrators about a new service purchase.

    Args:
        bot: Telegram bot instance
        admin_ids: List of admin Telegram IDs
        service: Service instance containing purchase details
        seller: Seller instance who made the purchase
    """
    try:
        admin_message = (
            f"🔔 سرویس جدید خریداری شد\n\n"
            f"{html.bold('فروشنده:')} {seller.username} (کد: {seller.id})\n"
            f"{html.bold('شناسه سرویس:')} {html.code(service.id)}\n"
            f"{html.bold('شناسه کانفیگ:')} {public_id}\n"
            f"{html.bold('تعرفه:')} {service.tariff.description}\n"
            f"{html.bold('قیمت فروشنده:')} {format_currency(service.seller_price, convert_to_farsi=True)} تومان \n"
            f"{html.bold('قیمت اصلی:')} {format_currency(service.original_price, convert_to_farsi=True)} تومان \n"
            f"{html.bold('تاریخ:')} {convert_to_shamsi(service.created_at)}\n"
            f"{html.bold('وضعیت:')} {service.status.value}"
        )

        logger.info(
            f"Sending purchase notification to {len(admin_ids)} admins for service {service.id}"
        )

        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, admin_message, parse_mode="HTML")
                logger.debug(
                    f"Successfully notified admin {admin_id} about service {service.id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to notify admin {admin_id}: {str(e)}", exc_info=True
                )

    except Exception as e:
        logger.error(f"Error in notify_admins: {str(e)}", exc_info=True)


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
    logger.info(f"Starting purchase process for seller {seller.id}")

    try:
        # Extract and validate tariff ID
        try:
            tariff_id = UUID(callback.data.split("_")[1])
            logger.debug(f"Processing purchase for tariff {tariff_id}")
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid tariff ID format: {str(e)}")
            await callback.answer("فرمت شناسه تعرفه نامعتبر است.", show_alert=True)
            return

        # Get tariff details
        tariff = await repo.tariffs.get_tariff_details(tariff_id)
        if not tariff:
            logger.warning(f"Tariff {tariff_id} not found")
            await callback.answer("تعرفه مورد نظر یافت نشد.", show_alert=True)
            return

        # Check debt limit
        total_cost = tariff.price * (1 - seller.discount_percent / 100)
        if seller.current_debt + total_cost > seller.debt_limit:
            logger.warning(
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
            logger.warning(
                f"No available interface found for service type {tariff.service_type}"
            )
            await callback.answer(
                "در حال حاضر سرور مناسب در دسترس نیست. لطفاً بعداً تلاش کنید.",
                show_alert=True,
            )
            return

        # Process purchase
        logger.info(
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

        logger.info(f"Successfully completed purchase process for service {service.id}")

    except ValueError as e:
        logger.error(f"Validation error in purchase: {str(e)}", exc_info=True)
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.error(f"Error processing purchase: {str(e)}", exc_info=True)
        await callback.answer(
            "خطا در پردازش خرید. لطفاً دوباره تلاش کنید.", show_alert=True
        )
