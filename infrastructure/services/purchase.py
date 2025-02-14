# infrastructure/services/purchase.py
import logging
from datetime import datetime, timezone

from aiogram.types import BufferedInputFile

from infrastructure.database.models import (
    Service,
    ServiceStatus,
    Seller,
    Tariff,
    Interface,
    Peer,
)
from infrastructure.database.models.transactions import Transaction, TransactionType
from infrastructure.database.repo.requests import RequestsRepo
from infrastructure.services.wireguard import WireguardManager
from tgbot.models.wireguard import WireguardConfig, PurchaseData, WireguardPeerConfig

logger = logging.getLogger(__name__)


class PurchaseService:
    def __init__(self, repo: RequestsRepo):
        self.repo = repo
        self.wg_manager = None

    async def _init_wireguard_manager(self, interface: Interface) -> None:
        """Initialize WireGuard manager with configuration from the interface's router"""
        try:
            router = interface.router
            config = WireguardConfig(
                router_host=router.hostname,
                router_user=router.username,
                router_password=router.password,
                router_port=router.api_port,
                subnet=interface.network_subnet,
                dns_servers=interface.dns_servers,
                public_key=interface.public_key,
                allowed_ips=interface.allowed_ips,
                endpoint=interface.endpoint,
            )
            self.wg_manager = WireguardManager(config)
            logger.info(
                f"Initialized WireguardManager for interface {interface.interface_name}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize WireguardManager: {e}", exc_info=True)
            raise

    async def _create_wireguard_peer(
        self, service: Service, interface: Interface
    ) -> tuple[WireguardPeerConfig, str, str]:
        """Create WireGuard peer configuration on router"""
        try:
            purchase_data = PurchaseData(
                interface_name=interface.interface_name,
                seller_id=service.seller_id,
                purchase_id=service.id,
            )

            logger.info(
                f"Creating WireGuard peer for service {service.id} on interface {interface.interface_name}"
            )
            peer_config, config_file, qr_code = await self.wg_manager.create_peer(
                interface_name=interface.interface_name, purchase_data=purchase_data
            )

            logger.info(f"Successfully created WireGuard peer for service {service.id}")
            return peer_config, config_file, qr_code
        except Exception as e:
            logger.error(f"Failed to create WireGuard peer: {e}", exc_info=True)
            raise

    async def process_purchase(
        self, seller: Seller, tariff: Tariff, interface: Interface
    ) -> tuple[Service, str, BufferedInputFile, str]:
        """Process a service purchase"""
        logger.info(
            f"Starting purchase process for seller {seller.id}, tariff {tariff.id}"
        )

        try:
            # Initialize WireGuard manager
            await self._init_wireguard_manager(interface)

            # Calculate prices
            original_price = tariff.price
            seller_price = original_price * (1 - seller.discount_percent / 100)
            logger.info(
                f"Calculated prices: original={original_price}, seller={seller_price}"
            )

            # Create service record
            service_data = Service(
                seller_id=seller.id,
                tariff_id=tariff.id,
                interface_id=interface.id,
                purchase_date=datetime.now(timezone.utc),
                status=ServiceStatus.INACTIVE,
                original_price=original_price,
                seller_price=seller_price,
            )
            service = await self.repo.services.create_service(service_data)
            logger.info(f"Created service record with ID {service.id}")

            # Create WireGuard peer
            peer_config, config_file, qr_code = await self._create_wireguard_peer(
                service, interface
            )
            public_id = (
                f"{interface.interface_name}_{peer_config.allowed_ip.split('.')[-1]}"
            )

            # Create peer record
            peer_data = Peer(
                public_id=public_id,
                private_key=peer_config.private_key,
                public_key=peer_config.public_key,
                allocated_ip=peer_config.allowed_ip,
                dns_servers=interface.dns_servers,
                end_point=f"{interface.endpoint}",
                config_file=config_file,
                peer_comment=peer_config.comment,
            )
            peer = await self.repo.peers.create_peer(peer_data)
            logger.info(f"Created peer record for service {service.id}")

            # Create config file with proper naming
            config_filename = f"{public_id}.conf"
            config_document = BufferedInputFile(
                file=config_file.encode("utf-8"), filename=config_filename
            )
            logger.info(f"Generated config file: {config_filename}")

            # Record transaction
            transaction = Transaction(
                seller_id=seller.id,
                service_id=service.id,
                amount=seller_price,
                transaction_type=TransactionType.PURCHASE,
                description=f"Purchase of {tariff.description}",
            )
            await self.repo.transactions.create_transaction(transaction)
            logger.info(f"Recorded transaction for service {service.id}")

            # Update seller debt
            await self.repo.sellers.update_seller_dept(
                seller_id=seller.id,
                seller_price=seller_price,
                profit=original_price - seller_price,
            )
            logger.info(f"Updated seller {seller.id} debt")

            # Update service with peer ID
            await self.repo.services.update_peer_id(
                service_id=service.id, peer_id=peer.id
            )

            # Increment interface counter
            await self.repo.interfaces.increment_interface_counter(
                interface_id=interface.id
            )
            logger.info(f"Updated interface {interface.id} counter")

            logger.info(
                f"Successfully completed purchase process for service {service.id}"
            )
            return service, qr_code, config_document, public_id

        except Exception as e:
            logger.error(f"Purchase process failed: {e}", exc_info=True)
            raise
