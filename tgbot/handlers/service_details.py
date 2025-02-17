# tgbot/handlers/service_details.py

import logging
from uuid import UUID

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
    BufferedInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models import ServiceStatus, Service
from infrastructure.database.models.sellers import Seller
from infrastructure.database.repo.requests import RequestsRepo
from infrastructure.services.wireguard import WireguardManager
from tgbot.handlers.helper.purchase import show_loading_status
from tgbot.models.wireguard import WireguardConfig
from tgbot.services.back_button import add_return_buttons
from tgbot.services.utils import (
    convert_english_digits_to_farsi,
    format_currency,
    convert_to_shamsi,
    generate_qr_code,
)
from tgbot.states.service import ServiceStates

service_details_router = Router()

# Callback data prefixes for different actions
SERVICE_ACTION_PREFIX = {
    "VIEW": "service_view_",
    "ENABLE": "service_enable_",
    "DISABLE": "service_disable_",
    "RESET_KEY": "service_reset_",
    "RENEW": "service_renew_",
    "GET_CONFIG": "service_config_",
    "SET_NAME": "service_name_",
}


def create_service_details_keyboard(service: Service) -> InlineKeyboardMarkup:
    """Create keyboard for service details with all available actions."""
    builder = InlineKeyboardBuilder()

    # First row: Status toggle and Reset key
    if service.status == ServiceStatus.ACTIVE:
        builder.button(
            text="❌ غیرفعال کردن",
            callback_data=f"{SERVICE_ACTION_PREFIX['DISABLE']}{service.id}",
        )
    else:
        builder.button(
            text="✅ فعال کردن",
            callback_data=f"{SERVICE_ACTION_PREFIX['ENABLE']}{service.id}",
        )
    builder.button(
        text="🔄 تعویض کلید",
        callback_data=f"{SERVICE_ACTION_PREFIX['RESET_KEY']}{service.id}",
    )

    # Second row: Renew and Config
    builder.button(
        text="📅 تمدید",
        callback_data=f"{SERVICE_ACTION_PREFIX['RENEW']}{service.id}",
    )
    builder.button(
        text="📁 دریافت کانفیگ",
        callback_data=f"{SERVICE_ACTION_PREFIX['GET_CONFIG']}{service.id}",
    )

    # Third row: Set name
    builder.button(
        text="✏️ تنظیم نام دلخواه",
        callback_data=f"{SERVICE_ACTION_PREFIX['SET_NAME']}{service.id}",
    )

    # Adjust keyboard layout: 2 buttons per row except last row
    builder.adjust(2, 2, 1)

    # Add return buttons
    add_return_buttons(builder, "services", include_main_menu=True)

    return builder.as_markup()


def format_service_details(service: Service) -> str:
    """Format service details text."""
    # Define status emojis for different states
    status_emojis = {
        ServiceStatus.UNUSED: "⚪",  # White circle for unused
        ServiceStatus.INACTIVE: "🔴",  # Red circle for inactive
        ServiceStatus.ACTIVE: "🟢",  # Green circle for active
        ServiceStatus.EXPIRED: "🟡",  # Yellow circle for expired
        ServiceStatus.DELETED: "⚫",  # Black circle for deleted
    }

    status_emoji = status_emojis.get(service.status, "❓")

    # Format dates
    purchase_date = (
        convert_to_shamsi(service.purchase_date) if service.purchase_date else "-"
    )
    first_connect = (
        convert_to_shamsi(service.activation_date) if service.activation_date else "-"
    )
    expiry_date = convert_to_shamsi(service.expiry_date) if service.expiry_date else "-"
    deletion_date = (
        convert_to_shamsi(service.deletion_date) if service.deletion_date else "-"
    )
    last_handshake = (
        convert_to_shamsi(service.last_handshake) if service.last_handshake else "-"
    )

    # Format traffic data (assuming bytes, convert to MB)
    total_traffic = (
        f"{service.total_bytes / (1024 * 1024):.2f} MB"
        if service.total_bytes
        else "0 MB"
    )
    download_traffic = (
        f"{service.download_bytes / (1024 * 1024):.2f} MB"
        if service.download_bytes
        else "0 MB"
    )
    upload_traffic = (
        f"{service.upload_bytes / (1024 * 1024):.2f} MB"
        if service.upload_bytes
        else "0 MB"
    )

    return (
        f"🔖 شناسه سرویس: {convert_english_digits_to_farsi(str(service.peer.public_id) if service.peer else 'N/A')}\n"
        f"🔖 نام سرویس: {service.custom_name or '-'}\n"
        f"#️⃣ توضیحات فروشنده: {service.custom_name or '-'}\n"
        f"📅 تاریخ خرید: {purchase_date}\n"
        f"📅 تاریخ اتصال اولیه: {first_connect}\n"
        f"⏳ تاریخ انقضا: {expiry_date}\n"
        f"🗑️ تاریخ حذف: {deletion_date}\n"
        f"🌐 آدرس آی‌پی: {convert_english_digits_to_farsi(service.peer.allocated_ip or '-')}\n"
        f"📥 حجم کل داده مصرفی: {convert_english_digits_to_farsi(total_traffic)}\n"
        f"📲 داده دریافتی: {convert_english_digits_to_farsi(download_traffic)}\n"
        f"📤 داده ارسالی: {convert_english_digits_to_farsi(upload_traffic)}\n"
        f"🤝 هند شیک: {convert_english_digits_to_farsi(last_handshake)}\n"
        f"🚦 وضعیت سرویس: {status_emoji}\n"
        f"💰 قیمت: {format_currency(service.seller_price, convert_to_farsi=True)} تومان\n"
    )


@service_details_router.message(ServiceStates.waiting_for_name)
async def finish_set_custom_name(
    message: Message, state: FSMContext, seller: Seller, repo: RequestsRepo
):
    """Complete the process of setting a custom name."""
    try:
        # Get data from state
        data = await state.get_data()
        service_id = UUID(data["service_id"])
        prompt_message_id = data.get("prompt_message_id")

        # Get service to verify ownership
        service = await repo.services.get_service(service_id)
        if not service or service.seller_id != seller.id:
            await message.answer("❌ سرویس مورد نظر یافت نشد.")
            await state.clear()
            return

        # Update custom name
        await repo.services.update_service_custom_name(service_id, message.text)

        # Delete the prompt message if we have its ID
        if prompt_message_id:
            try:
                await message.bot.delete_message(message.chat.id, prompt_message_id)
            except Exception as e:
                logging.warning(f"Failed to delete prompt message: {e}")

        # Delete the user's input message
        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Failed to delete user input message: {e}")

        # Clear state
        await state.clear()

        # Get updated service
        service = await repo.services.get_service(service_id)

        # Send confirmation with updated service details
        await message.answer(
            "✅ نام دلخواه با موفقیت تنظیم شد.\n\n" + format_service_details(service),
            reply_markup=create_service_details_keyboard(service),
        )

    except Exception as e:
        logging.error(f"Error in finish_set_custom_name: {e}", exc_info=True)
        await message.answer("❌ خطا در تنظیم نام دلخواه.")
        await state.clear()


# For viewing service details
@service_details_router.callback_query(F.data.startswith(SERVICE_ACTION_PREFIX["VIEW"]))
async def show_service_details(
    callback: CallbackQuery, seller: Seller, repo: RequestsRepo
):
    """Handle service details view."""
    try:
        logging.info("show_service_details handler called")
        service_id = UUID(callback.data.removeprefix(SERVICE_ACTION_PREFIX["VIEW"]))
        service = await repo.services.get_service(service_id)

        if not service or service.seller_id != seller.id:
            await callback.answer("❌ سرویس مورد نظر یافت نشد.", show_alert=True)
            return

        text = format_service_details(service)
        await callback.message.edit_text(
            text=text, reply_markup=create_service_details_keyboard(service)
        )

    except Exception as e:
        logging.error(f"Error in show_service_details: {e}", exc_info=True)
        await callback.answer("❌ خطا در نمایش جزئیات سرویس.", show_alert=True)


# For setting custom name
@service_details_router.callback_query(
    F.data.startswith(SERVICE_ACTION_PREFIX["SET_NAME"])
)
async def start_set_custom_name(
    callback: CallbackQuery, state: FSMContext, seller: Seller, repo: RequestsRepo
):
    """Start the process of setting a custom name."""
    try:
        logging.info("start_set_custom_name handler called")
        service_id = UUID(callback.data.removeprefix(SERVICE_ACTION_PREFIX["SET_NAME"]))
        service = await repo.services.get_service(service_id)

        if not service or service.seller_id != seller.id:
            await callback.answer("❌ سرویس مورد نظر یافت نشد.", show_alert=True)
            return

        # Store service_id and prompt_message_id in state
        await state.set_state(ServiceStates.waiting_for_name)

        # Send prompt message and store its message_id
        prompt_message = await callback.message.answer(
            "✏️ لطفاً نام دلخواه جدید را وارد کنید:"
        )
        await state.update_data(
            service_id=str(service_id), prompt_message_id=prompt_message.message_id
        )

        await callback.answer()

    except Exception as e:
        logging.error(f"Error in start_set_custom_name: {e}", exc_info=True)
        await callback.answer("❌ خطا در شروع فرآیند تنظیم نام.", show_alert=True)


@service_details_router.callback_query(
    F.data.startswith(SERVICE_ACTION_PREFIX["GET_CONFIG"])
)
async def handle_get_config(
    callback: CallbackQuery, seller: Seller, repo: RequestsRepo
) -> None:
    try:
        logging.info("handle_get_config handler called")
        service_id = UUID(
            callback.data.removeprefix(SERVICE_ACTION_PREFIX["GET_CONFIG"])
        )
        service = await repo.services.get_service_with_peer(service_id)

        if not service or service.seller_id != seller.id:
            await callback.answer("❌ سرویس مورد نظر یافت نشد.", show_alert=True)
            return

        if not service.peer:
            await callback.answer(
                "❌ اطلاعات پیکربندی برای این سرویس موجود نیست.", show_alert=True
            )
            return

        # Generate QR code
        qr_code_url = await generate_qr_code(service.peer.config_file)  # type: ignore

        # Create config file document
        config_document = BufferedInputFile(
            file=service.peer.config_file.encode("utf-8"),  # type: ignore
            filename=f"wireguard_{service.peer.public_id}.conf",  # type: ignore
        )

        await callback.message.answer_document(
            document=config_document,
            caption=f"🔰 فایل پیکربندی سرویس {service.peer.public_id}",  # type: ignore
        )

        await callback.message.answer_photo(
            photo=qr_code_url,
            caption=f" 🔄 کد QR پیکربندی سرویس {service.peer.public_id}",  # type: ignore
        )

        await callback.answer()

    except Exception as e:
        logging.error(f"Error in handle_get_config: {e}", exc_info=True)
        await callback.answer("❌ خطا در دریافت پیکربندی سرویس.", show_alert=True)


@service_details_router.callback_query(
    F.data.startswith(SERVICE_ACTION_PREFIX["DISABLE"])
)
async def disable_service(callback: CallbackQuery, seller: Seller, repo: RequestsRepo):
    """Handle service disable action."""
    try:
        logging.info("disable_service handler called")
        service_id = UUID(callback.data.removeprefix(SERVICE_ACTION_PREFIX["DISABLE"]))
        service = await repo.services.get_service(service_id)

        if not service or service.seller_id != seller.id:
            await callback.answer("❌ سرویس مورد نظر یافت نشد.", show_alert=True)
            return

        # Get WireGuard configuration
        wg_config = WireguardConfig(
            router_host=service.interface.router.hostname,
            router_port=service.interface.router.api_port,
            router_user=service.interface.router.username,
            router_password=service.interface.router.password,
            endpoint=service.interface.endpoint,
            public_key=service.interface.public_key,
            subnet=service.interface.network_subnet,
            dns_servers=service.interface.dns_servers,
            allowed_ips=service.interface.allowed_ips,
        )

        # Initialize WireGuard manager and disable peer
        wg_manager = WireguardManager(wg_config)
        success = await wg_manager.disable_peer(
            service.interface.interface_name, service.peer.peer_comment
        )

        if success:
            # Update service status in database
            await repo.services.update_service_status(
                service_id, ServiceStatus.INACTIVE
            )

            # Refresh service details
            service = await repo.services.get_service(service_id)

            await callback.message.edit_text(
                text=format_service_details(service),
                reply_markup=create_service_details_keyboard(service),
            )
            await callback.answer("✅ سرویس با موفقیت غیرفعال شد.", show_alert=True)
        else:
            await callback.answer("❌ خطا در غیرفعال‌سازی سرویس.", show_alert=True)

    except Exception as e:
        logging.error(f"Error in disable_service: {e}", exc_info=True)
        await callback.answer("❌ خطا در غیرفعال‌سازی سرویس.", show_alert=True)


@service_details_router.callback_query(
    F.data.startswith(SERVICE_ACTION_PREFIX["ENABLE"])
)
async def enable_service(callback: CallbackQuery, seller: Seller, repo: RequestsRepo):
    """Handle service enable action."""
    try:
        logging.info("Enable peer handler called")
        service_id = UUID(callback.data.removeprefix(SERVICE_ACTION_PREFIX["ENABLE"]))
        service = await repo.services.get_service(service_id)

        if not service or service.seller_id != seller.id:
            await callback.answer("❌ سرویس مورد نظر یافت نشد.", show_alert=True)
            return

        # Get WireGuard configuration
        wg_config = WireguardConfig(
            router_host=service.interface.router.hostname,
            router_port=service.interface.router.api_port,
            router_user=service.interface.router.username,
            router_password=service.interface.router.password,
            endpoint=service.interface.endpoint,
            public_key=service.interface.public_key,
            subnet=service.interface.network_subnet,
            dns_servers=service.interface.dns_servers,
            allowed_ips=service.interface.allowed_ips,
        )

        # Initialize WireGuard manager and enable peer
        wg_manager = WireguardManager(wg_config)
        success = await wg_manager.enable_peer(
            service.interface.interface_name, service.peer.peer_comment
        )

        if success:
            # Update service status in database
            await repo.services.update_service_status(service_id, ServiceStatus.ACTIVE)

            # Refresh service details
            service = await repo.services.get_service(service_id)

            await callback.message.edit_text(
                text=format_service_details(service),
                reply_markup=create_service_details_keyboard(service),
            )
            await callback.answer("✅ سرویس با موفقیت فعال شد.", show_alert=True)
        else:
            await callback.answer("❌ خطا در فعال‌سازی سرویس.", show_alert=True)

    except Exception as e:
        logging.error(f"Error in enable_service: {e}", exc_info=True)
        await callback.answer("❌ خطا در فعال‌سازی سرویس.", show_alert=True)


@service_details_router.callback_query(
    F.data.startswith(SERVICE_ACTION_PREFIX["RESET_KEY"])
)
async def handle_reset_key(callback: CallbackQuery, seller: Seller, repo: RequestsRepo):
    """Handle service key reset action."""
    try:
        logging.info("Reset key handler called")
        service_id = UUID(
            callback.data.removeprefix(SERVICE_ACTION_PREFIX["RESET_KEY"])
        )
        service = await repo.services.get_service(service_id)

        if not service or service.seller_id != seller.id:
            await callback.answer("❌ سرویس مورد نظر یافت نشد!", show_alert=True)
            return

        # Answer callback immediately to prevent timeout
        await callback.answer("⏳ در حال پردازش درخواست شما...")

        async with show_loading_status(callback.message, "⏳ در حال بازنشانی کلید..."):
            # Get WireGuard configuration
            wg_config = WireguardConfig(
                router_host=service.interface.router.hostname,
                router_port=service.interface.router.api_port,
                router_user=service.interface.router.username,
                router_password=service.interface.router.password,
                endpoint=service.interface.endpoint,
                public_key=service.interface.public_key,
                subnet=service.interface.network_subnet,
                dns_servers=service.interface.dns_servers,
                allowed_ips=service.interface.allowed_ips,
            )

            # Initialize WireGuard manager and reset peer
            wg_manager = WireguardManager(wg_config)
            result = await wg_manager.reset_peer(
                service.interface.interface_name, service.peer.peer_comment
            )

            if result:
                peer_config, config_file, qr_code = result

                # Update peer information in database
                await repo.peers.update_peer_keys(
                    service.peer.id,
                    private_key=peer_config.private_key,
                    public_key=peer_config.public_key,
                    config_file=config_file,
                )

                # Create config file document
                config_document = BufferedInputFile(
                    file=config_file.encode("utf-8"),
                    filename=f"wireguard_{service.peer.public_id}.conf",
                )

                # Send new configuration
                await callback.message.answer_photo(
                    photo=qr_code, caption="🔄 کلید سرویس با موفقیت بازنشانی شد!"
                )

                await callback.message.answer_document(
                    document=config_document,
                    caption=f"📁 فایل کانفیگ سرویس {service.peer.public_id}",
                )

                # Get fresh service details
                updated_service = await repo.services.get_service(service_id)
                new_text = format_service_details(updated_service)
                new_keyboard = create_service_details_keyboard(updated_service)

                # Check if the content would actually change
                current_text = callback.message.text
                if current_text != new_text:
                    try:
                        await callback.message.edit_text(
                            text=new_text, reply_markup=new_keyboard
                        )
                    except TelegramBadRequest as e:
                        if "message is not modified" not in str(e):
                            raise
                        logging.debug("Message content was identical, skipping update")
            else:
                await callback.message.answer(
                    "❌ خطا در بازنشانی کلید. لطفا دوباره تلاش کنید."
                )

    except Exception as e:
        logging.error(f"Error in handle_reset_key: {e}", exc_info=True)
        await callback.message.answer("❌ خطا در بازنشانی کلید. لطفا دوباره تلاش کنید.")
