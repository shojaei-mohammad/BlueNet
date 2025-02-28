# infrastructure/scheduler/scheduler.py
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from aiogram import Bot, html
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import async_sessionmaker

from infrastructure.database.models.services import Service, ServiceStatus
from infrastructure.database.repo.requests import RequestsRepo
from infrastructure.services.wireguard import WireguardManager
from tgbot.config import Config
from tgbot.models.wireguard import WireguardConfig
from tgbot.services.utils import convert_to_shamsi


class VPNAccountingService:
    MESSAGES_PER_SECOND = 30
    MESSAGES_PER_MINUTE = 20

    def __init__(self, session_pool: async_sessionmaker, bot: Bot, config: Config):
        self.session_pool = session_pool
        self.bot = bot
        self.config = config
        self._messages_sent_last_second = 0
        self._messages_sent_last_minute = 0
        self._last_second = 0
        self._last_minute = 0
        # Initialize WireguardManager for each interface
        self.wg_managers = {}

    async def initialize_wg_managers(self):
        """Initialize WireGuard managers for all active interfaces"""
        async with self.session_pool() as session:
            repo = RequestsRepo(session)
            interfaces = await repo.interfaces.get_active_interfaces()

            for interface in interfaces:
                # Create WireGuard configuration for this interface
                wg_config = WireguardConfig(
                    router_host=interface.router.hostname,  # type: ignore
                    router_user=interface.router.username,
                    router_password=interface.router.password,
                    router_port=interface.router.api_port,
                    public_key=interface.public_key,
                    endpoint=f"{interface.endpoint}",
                    allowed_ips=interface.allowed_ips,
                    dns_servers=interface.dns_servers,
                    subnet=interface.network_subnet,
                )

                # Create WireguardManager for this interface
                self.wg_managers[interface.id] = WireguardManager(wg_config)

            logging.info(f"Initialized {len(self.wg_managers)} WireGuard managers")

    async def track_first_usage(self):
        """
        Check for services that have been purchased but not yet activated.
        If the handshake value is not 0, it means the user has started using the service.
        Update the activation_date, expiry_date, deletion_date, and status accordingly.
        """
        logging.info("Starting to track first usage of VPN services")

        try:
            async with self.session_pool() as session:
                repo = RequestsRepo(session)

                # Get inactive services with peers
                inactive_services = (
                    await repo.services.get_inactive_services_with_peers()
                )

                if not inactive_services:
                    logging.info("No inactive services found for first usage tracking")
                    return

                logging.info(
                    f"Found {len(inactive_services)} inactive services to check"
                )

                # Ensure WG managers are initialized
                if not self.wg_managers:
                    await self.initialize_wg_managers()

                for service in inactive_services:
                    if not service.peer:
                        logging.warning(
                            f"Service {service.id} has no associated peer, skipping"
                        )
                        continue

                    # Get the appropriate WG manager
                    wg_manager = self.wg_managers.get(service.interface_id)
                    if not wg_manager:
                        logging.warning(
                            f"No WG manager found for interface {service.interface_id}, skipping"
                        )
                        continue

                    # Check handshake status on the router using the WireguardManager
                    (
                        is_active,
                        raw_handshake,
                    ) = await wg_manager.get_peer_handshake_status(
                        service.interface.interface_name, service.peer.peer_comment  # type: ignore
                    )

                    if is_active:
                        # Get current time
                        now = datetime.now()

                        # Calculate expiry date based on tariff duration
                        expiry_date = now + timedelta(days=service.tariff.duration_days)

                        # Calculate deletion date based on expiry date plus grace period

                        deletion_date = expiry_date + timedelta(
                            days=self.config.wg.deletion_grace_period
                        )

                        # Update service status and dates
                        await repo.services.update_service(
                            service_id=service.id,
                            activation_date=now,
                            expiry_date=expiry_date,
                            deletion_date=deletion_date,
                            status=ServiceStatus.ACTIVE,
                            last_handshake=raw_handshake,  # Store the raw value
                            updated_at=datetime.now(timezone.utc).replace(
                                microsecond=0
                            ),
                        )

                        # Notify user about service activation
                        await self._notify_service_activation(service)

                        logging.info(
                            f"Service {service.id} activated for the first time. "
                            f"Expiry: {expiry_date.isoformat()}, Deletion: {deletion_date.isoformat()}, "
                            f"Handshake: {raw_handshake}"
                        )

        except Exception as e:
            logging.error(f"Error tracking first usage: {str(e)}", exc_info=True)

    async def update_usage_data(self):
        """
        Update usage data for active services.
        This includes last handshake time and data usage metrics.
        """
        logging.info("Starting to update VPN usage data")

        try:
            async with self.session_pool() as session:
                repo = RequestsRepo(session)

                # Get active services with peers
                active_services = await repo.services.get_active_services_with_peers()

                if not active_services:
                    logging.info("No active services found for usage tracking")
                    return

                logging.info(f"Found {len(active_services)} active services to update")

                # Ensure WG managers are initialized
                if not self.wg_managers:
                    await self.initialize_wg_managers()

                for service in active_services:
                    if not service.peer:
                        logging.warning(
                            f"Service {service.id} has no associated peer, skipping"
                        )
                        continue

                    # Get the appropriate WG manager
                    wg_manager = self.wg_managers.get(service.interface_id)
                    if not wg_manager:
                        logging.warning(
                            f"No WG manager found for interface {service.interface_id}, skipping"
                        )
                        continue

                    # Get peer usage data using the WireguardManager
                    usage_data = await wg_manager.get_peer_usage_data(
                        service.interface.interface_name, service.peer.peer_comment  # type: ignore
                    )

                    if usage_data:
                        # Update service with usage data
                        await repo.services.update_service_usage(
                            service_id=service.id,
                            last_handshake=usage_data.get("last_handshake"),
                            download_bytes=usage_data.get("download_bytes"),
                            upload_bytes=usage_data.get("upload_bytes"),
                            total_bytes=usage_data.get("total_bytes"),
                        )

                        logging.info(f"Updated usage data for service {service.id}")

        except Exception as e:
            logging.error(f"Error updating usage data: {str(e)}", exc_info=True)

    async def disable_expired_services(self):
        """
        Check for services that have expired and disable them.
        This involves disabling the peer on the router and updating the service status.
        """
        logging.info("Starting to disable expired VPN services")

        try:
            async with self.session_pool() as session:
                repo = RequestsRepo(session)

                # Get expired services that are still active
                expired_services = await repo.services.get_expired_services()

                if not expired_services:
                    logging.info("No expired services found")
                    return

                logging.info(
                    f"Found {len(expired_services)} expired services to disable"
                )

                # Ensure WG managers are initialized
                if not self.wg_managers:
                    await self.initialize_wg_managers()

                for service in expired_services:
                    if not service.peer:
                        logging.warning(
                            f"Service {service.id} has no associated peer, skipping"
                        )
                        continue

                    # Get the appropriate WG manager
                    wg_manager = self.wg_managers.get(service.interface_id)
                    if not wg_manager:
                        logging.warning(
                            f"No WG manager found for interface {service.interface_id}, skipping"
                        )
                        continue

                    # Disable peer on the router using the WireguardManager
                    success = await wg_manager.disable_peer(
                        service.interface.interface_name, service.peer.peer_comment  # type: ignore
                    )

                    if success:
                        # Update service status
                        await repo.services.update_service(
                            service_id=service.id,
                            status=ServiceStatus.EXPIRED,
                            updated_at=datetime.now(timezone.utc).replace(
                                microsecond=0
                            ),
                        )

                        # Notify user about service expiration
                        await self._notify_service_expiration(service)

                        logging.info(
                            f"Service {service.id} marked as expired and disabled"
                        )
                    else:
                        logging.error(
                            f"Failed to disable peer for expired service {service.id}"
                        )

        except Exception as e:
            logging.error(f"Error disabling expired services: {str(e)}", exc_info=True)

    async def delete_expired_services(self):
        """
        Delete services that have passed their deletion date.
        This involves removing the peer from the router and updating the service status to DELETED.
        """
        logging.info("Starting to delete services past deletion date")

        try:
            async with self.session_pool() as session:
                repo = RequestsRepo(session)

                # Get services that have passed their deletion date
                deletion_due_services = (
                    await repo.services.get_services_past_deletion_date()
                )

                if not deletion_due_services:
                    logging.info("No services found that need to be deleted")
                    return

                logging.info(f"Found {len(deletion_due_services)} services to delete")

                # Ensure WG managers are initialized
                if not self.wg_managers:
                    await self.initialize_wg_managers()

                for service in deletion_due_services:
                    if not service.peer:
                        logging.warning(
                            f"Service {service.id} has no associated peer, skipping"
                        )
                        continue

                    # Get the appropriate WG manager
                    wg_manager = self.wg_managers.get(service.interface_id)
                    if not wg_manager:
                        logging.warning(
                            f"No WG manager found for interface {service.interface_id}, skipping"
                        )
                        continue

                    # Delete peer from the router using the new delete_peer method
                    success = await wg_manager.delete_peer(
                        service.interface.interface_name, service.peer.peer_comment  # type: ignore
                    )

                    if success:
                        # Update service status
                        await repo.services.update_service(
                            service_id=service.id,
                            status=ServiceStatus.DELETED,
                            updated_at=datetime.now(timezone.utc).replace(
                                microsecond=0
                            ),
                        )

                        # Notify user about service deletion
                        await self._notify_service_deletion(service)

                        logging.info(
                            f"Service {service.id} marked as deleted and removed from router"
                        )
                    else:
                        logging.error(f"Failed to delete peer for service {service.id}")

        except Exception as e:
            logging.error(f"Error deleting expired services: {str(e)}", exc_info=True)

    async def notify_expiring_services(self):
        """
        Notify sellers about their services that will expire in 3 days.
        Groups services by seller and sends a consolidated list.
        """
        logging.info("Starting to notify about services expiring in 3 days")

        try:
            async with self.session_pool() as session:
                repo = RequestsRepo(session)

                # Get services expiring in 3 days
                expiring_services = await repo.services.get_services_expiring_soon(
                    days_threshold=3
                )

                if not expiring_services:
                    logging.info("No services found that are expiring in 3 days")
                    return

                logging.info(
                    f"Found {len(expiring_services)} services expiring in 3 days"
                )

                # Group services by seller
                services_by_seller = {}
                for service in expiring_services:
                    seller_id = service.seller_id
                    if seller_id not in services_by_seller:
                        services_by_seller[seller_id] = []
                    services_by_seller[seller_id].append(service)

                # Send notifications to each seller
                for seller_id, services in services_by_seller.items():
                    await self._notify_seller_about_expiring_services(services)

        except Exception as e:
            logging.error(
                f"Error notifying about expiring services: {str(e)}", exc_info=True
            )

    async def _notify_service_activation(self, service: Service):
        """Send notification to user about service activation"""
        try:
            # Get user's chat ID from seller
            chat_id = service.seller.chat_id  # type: ignore
            if not chat_id:
                logging.warning(
                    f"No chat ID found for seller {service.seller_id}, skipping notification"
                )
                return

            # Format expiry date
            expiry_date_str = convert_to_shamsi(service.expiry_date)

            # Create message
            message = (
                f"🎉 {html.bold('اعلان فعال‌سازی سرویس')} 🎉\n\n"
                f"کاربر گرامی، سرویس VPN شما {html.bold('فعال شده است')}.\n\n"
                f"📌 {html.bold('مشخصات سرویس:')}\n"
                f"🔹 {html.bold('نام سرویس:')} {service.peer.public_id or '---'}\n"
                f"🔹 {html.bold('تعرفه:')} {service.tariff.description}\n"  # type: ignore
                f"🔹 {html.bold('تاریخ انقضا:')} {expiry_date_str}\n\n"
            )

            # Send message
            await self._send_rate_limited_message(chat_id, message)
            logging.info(
                f"Sent activation notification for service {service.id} to user {chat_id}"
            )

        except Exception as e:
            logging.error(f"Error sending activation notification: {str(e)}")

    async def _notify_service_expiration(self, service: Service):
        """Send notification to user about service expiration"""
        try:
            # Get user's chat ID from seller
            chat_id = service.seller.chat_id
            if not chat_id:
                logging.warning(
                    f"No chat ID found for seller {service.seller_id}, skipping notification"
                )
                return

            # Format expiry date
            expiry_date_str = convert_to_shamsi(service.expiry_date)

            # Create message
            message = (
                f"⚠️ {html.bold('اعلان انقضای سرویس')} ⚠️\n\n"
                f"کاربر گرامی، سرویس VPN شما {html.bold('منقضی شده است')}.\n\n"
                f"📌 {html.bold('مشخصات سرویس:')}\n"
                f"🔹 {html.bold('نام سرویس:')} {service.peer.public_id or '---'}\n"
                f"🔹 {html.bold('تعرفه:')} {service.tariff.description}\n"  # type: ignore
                f"🔹 {html.bold('تاریخ انقضا:')} {expiry_date_str}\n\n"
                f"🔄 برای ادامه استفاده از سرویس، لطفاً نسبت به تمدید آن اقدام فرمایید."
            )

            # Create button for renewal
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="تمدید سرویس",
                            callback_data=f"service_renew_{service.id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="مشاهده سرویس",
                            callback_data=f"service_view_{service.id}",
                        )
                    ],
                ]
            )

            # Send message
            await self._send_rate_limited_message(chat_id, message, keyboard)
            logging.info(
                f"Sent expiration notification for service {service.id} to user {chat_id}"
            )

        except Exception as e:
            logging.error(f"Error sending expiration notification: {str(e)}")

    async def _send_rate_limited_message(
        self, chat_id: int, text: str, markup: Optional[InlineKeyboardMarkup] = None
    ):
        """Send message with rate limiting"""
        current_time = asyncio.get_event_loop().time()

        # Reset counters if time window has passed
        if current_time - self._last_second >= 1:
            self._messages_sent_last_second = 0
            self._last_second = current_time
        if current_time - self._last_minute >= 60:
            self._messages_sent_last_minute = 0
            self._last_minute = current_time

        # Wait if rate limits are exceeded
        while (
            self._messages_sent_last_second >= self.MESSAGES_PER_SECOND
            or self._messages_sent_last_minute >= self.MESSAGES_PER_MINUTE
        ):
            await asyncio.sleep(0.1)
            current_time = asyncio.get_event_loop().time()

            if current_time - self._last_second >= 1:
                self._messages_sent_last_second = 0
                self._last_second = current_time
            if current_time - self._last_minute >= 60:
                self._messages_sent_last_minute = 0
                self._last_minute = current_time

        # Send message and update counters
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
        self._messages_sent_last_second += 1
        self._messages_sent_last_minute += 1

    async def _notify_service_deletion(self, service: Service):
        """Send notification to user about service deletion"""
        try:
            # Get user's chat ID from seller
            chat_id = service.seller.chat_id
            if not chat_id:
                logging.warning(
                    f"No chat ID found for seller {service.seller_id}, skipping notification"
                )
                return

            # Format dates
            expiry_date_str = convert_to_shamsi(service.expiry_date)
            deletion_date_str = convert_to_shamsi(service.deletion_date)

            # Create message
            message = (
                f"🗑️ {html.bold('اعلان حذف سرویس')} 🗑️\n\n"
                f"کاربر گرامی، سرویس VPN شما {html.bold('حذف شده است')}.\n\n"
                f"📌 {html.bold('مشخصات سرویس:')}\n"
                f"🔹 {html.bold('نام سرویس:')} {service.peer.public_id or '---'}\n"
                f"🔹 {html.bold('تعرفه:')} {service.tariff.description}\n"  # type: ignore
                f"🔹 {html.bold('تاریخ انقضا:')} {expiry_date_str}\n"
                f"🔹 {html.bold('تاریخ حذف:')} {deletion_date_str}\n\n"
                f"⚠️ این سرویس به دلیل عدم تمدید به طور کامل از سیستم حذف شده است. "
                f"برای خرید سرویس جدید، لطفاً از منوی اصلی اقدام نمایید."
            )

            # Send message
            await self._send_rate_limited_message(chat_id, message)
            logging.info(
                f"Sent deletion notification for service {service.id} to user {chat_id}"
            )

        except Exception as e:
            logging.error(f"Error sending deletion notification: {str(e)}")

    async def _notify_seller_about_expiring_services(self, services: list[Service]):
        """
        Send a notification to a seller about their services that will expire soon.

        Args:
            services: List of services belonging to the same seller that will expire soon
        """
        if not services:
            return

        try:
            # Get the seller's chat ID (all services belong to the same seller)
            seller = services[0].seller
            chat_id = seller.chat_id

            if not chat_id:
                logging.warning(
                    f"No chat ID found for seller {seller.id}, skipping notification"
                )
                return

            # Format expiry date (should be the same for all services in this notification)
            expiry_date = services[0].expiry_date
            expiry_date_str = convert_to_shamsi(expiry_date)

            # Create message header
            message = (
                f"⚠️ {html.bold('اعلان سرویس‌های در حال انقضا')} ⚠️\n\n"
                f"کاربر گرامی، سرویس‌های VPN زیر {html.bold('در تاریخ ' + expiry_date_str)} منقضی خواهند شد:\n\n"
            )

            # Add each service to the message
            for i, service in enumerate(services, 1):
                message += f"{i}. {html.code(service.peer.public_id)} \n"

            # Add footer with instructions
            message += (
                "\nلطفاً برای جلوگیری از قطع سرویس، نسبت به تمدید آنها اقدام نمایید."
                "با ضربه زدن برروی نام سرویس میتوانید آنرا کپی کرده و از قسمت جستجو جزییات را مشاهده کنید."
            )

            # Send message
            await self._send_rate_limited_message(chat_id, message)
            logging.info(
                f"Sent expiring services notification to user {chat_id} for {len(services)} services"
            )

        except Exception as e:
            logging.error(f"Error sending expiring services notification: {str(e)}")
