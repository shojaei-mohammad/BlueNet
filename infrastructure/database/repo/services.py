# infrastructure/database/repo/services.py
import logging
from datetime import datetime, timezone
from typing import Tuple, List, Optional
from uuid import UUID

from sqlalchemy import insert, update, select, func, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload

from infrastructure.database.models import Service, ServiceStatus, Interface, Peer
from infrastructure.database.repo.base import BaseRepo


class ServiceRepo(BaseRepo):
    async def create_service(self, service: Service):
        try:
            # Extract data from the SQLAlchemy model into a dictionary
            service_data = {
                "seller_id": service.seller_id,
                "tariff_id": service.tariff_id,
                "interface_id": service.interface_id,
                "purchase_date": service.purchase_date,
                "status": service.status,
                "original_price": service.original_price,
                "seller_price": service.seller_price,
            }

            # Create the insert statement
            insert_stmt = insert(Service).values(**service_data).returning(Service)

            # Execute the statement
            result = await self.session.execute(insert_stmt)
            await self.session.commit()

            # Return the inserted record
            return result.scalar_one()

        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Failed to create service: {e}")
            raise Exception("Failed to create service in the database.") from e

        except Exception as e:
            await self.session.rollback()
            logging.error(f"An unexpected error occurred: {e}")
            raise Exception(
                "An unexpected error occurred during database operations."
            ) from e

    async def update_peer_id(self, service_id: UUID, peer_id: UUID):
        try:
            stmt = (
                update(Service)
                .where(Service.id == service_id)
                .values(
                    peer_id=peer_id,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
            )
            await self.session.execute(stmt)
            await self.session.commit()
            logging.info(f"Updated service {service_id} with peer {peer_id}")

        except Exception as e:
            logging.error(f"Error updating service peer: {e}", exc_info=True)
            raise

    async def get_seller_services(
        self, seller_id: int, page: int = 1, per_page: int = 5
    ) -> Tuple[List[Service], int]:
        """
        Fetch paginated services for a seller with all necessary relations.

        Args:
            seller_id: The ID of the seller
            page: Page number (1-based)
            per_page: Number of items per page

        Returns:
            Tuple of (list of services, total count)
        """
        try:
            # Calculate offset
            offset = (page - 1) * per_page

            # Query to get total count
            count_query = (
                select(func.count())
                .select_from(Service)
                .where(Service.seller_id == seller_id)
            )
            total_count = await self.session.scalar(count_query) or 0

            # Query to get paginated services with relations
            query = (
                select(Service)
                .options(
                    joinedload(Service.peer),
                    joinedload(Service.tariff),
                    joinedload(Service.interface),
                )
                .where(Service.seller_id == seller_id)
                .order_by(Service.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )

            result = await self.session.execute(query)
            services = result.scalars().unique().all()

            return list(services), total_count

        except Exception as e:
            logging.error(f"Error fetching services for seller {seller_id}: {e}")
            raise

    async def get_service(self, service_id: UUID) -> Optional[Service]:
        """
        Get a service by its ID with all related information.

        Args:
            service_id: The ID of the service to retrieve

        Returns:
            Service object if found, None otherwise
        """
        try:
            # Create query joining Service with all necessary relationships
            query = (
                select(Service)
                .options(
                    selectinload(Service.peer),
                    selectinload(Service.tariff),
                    selectinload(Service.interface).selectinload(Interface.router),
                )
                .where(Service.id == service_id)
            )

            # Execute query
            result = await self.session.execute(query)
            service = result.scalar_one_or_none()

            return service

        except Exception as e:
            logging.error(f"Error fetching service {service_id}: {e}", exc_info=True)
            raise

    async def update_service_status(
        self, service_id: UUID, new_status: ServiceStatus
    ) -> bool:
        """
        Update the status of a service.

        Args:
            service_id: The ID of the service to update
            new_status: The new ServiceStatus to set

        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Create update statement
            stmt = (
                update(Service)
                .where(Service.id == service_id)
                .values(
                    status=new_status,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
                .returning(Service.id)
            )

            # Execute update
            result = await self.session.execute(stmt)
            await self.session.commit()

            # Check if any row was updated
            updated = result.scalar_one_or_none() is not None

            return updated

        except Exception as e:
            await self.session.rollback()
            logging.error(
                f"Error updating service {service_id} status to {new_status}: {e}",
                exc_info=True,
            )
            raise

    async def update_service_custom_name(
        self, service_id: UUID, custom_name: str
    ) -> bool:
        """
        Update the custom name of a service.

        Args:
            service_id: The ID of the service to update
            custom_name: The new custom name to set

        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Create update statement
            stmt = (
                update(Service)
                .where(Service.id == service_id)
                .values(
                    custom_name=custom_name,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
                .returning(Service.id)
            )

            # Execute update
            result = await self.session.execute(stmt)
            await self.session.commit()

            # Check if any row was updated
            updated = result.scalar_one_or_none() is not None

            return updated

        except Exception as e:
            await self.session.rollback()
            logging.error(
                f"Error updating service {service_id} custom name to {custom_name}: {e}",
                exc_info=True,
            )
            raise

    async def get_service_with_peer(self, service_id: UUID) -> Optional[Service]:
        """
        Get service with related peer information.

        Args:
            service_id: UUID of the service to retrieve

        Returns:
            Service object with peer information if found, None otherwise

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            logging.debug(
                f"Fetching service with peer information for service_id: {service_id}"
            )

            query = (
                select(Service)
                .options(
                    joinedload(Service.peer),
                    joinedload(Service.tariff),
                    joinedload(Service.interface),
                )
                .where(Service.id == service_id)
                .where(Service.status != ServiceStatus.DELETED)
            )

            result = await self.session.execute(query)
            service = result.scalar_one_or_none()

            if service:
                logging.info(f"Retrieved service {service_id}:")
            else:
                logging.warning(f"Service not found with id: {service_id}")

            return service

        except SQLAlchemyError as e:
            logging.error(
                f"Database error while fetching service {service_id} with peer: {str(e)}",
                exc_info=True,
            )
            raise e

        except Exception as e:
            logging.error(
                f"Unexpected error while fetching service {service_id} with peer: {str(e)}",
                exc_info=True,
            )
            raise e

    async def update_service_expiry(
        self, service_id: UUID, expiry_date: datetime, deletion_date: datetime
    ) -> bool:

        try:
            # Create update statement
            stmt = (
                update(Service)
                .where(Service.id == service_id)
                .values(
                    expiry_date=expiry_date,
                    deletion_date=deletion_date,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
                .returning(Service.id)
            )

            # Execute update
            result = await self.session.execute(stmt)
            await self.session.commit()

            # Check if any row was updated
            updated = result.scalar_one_or_none() is not None

            return updated

        except Exception as e:
            await self.session.rollback()
            logging.error(
                f"Error updating service {service_id} expiry date to {expiry_date}: {e}",
                exc_info=True,
            )
            raise

    async def get_service_by_public_id(
        self, seller_id: int, public_id: str
    ) -> Optional[Service]:
        """
        Get service by exact public ID match for a specific seller.

        Args:
            seller_id: The ID of the seller
            public_id: The public ID to search for

        Returns:
            Service object if found, None otherwise

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            logging.debug(
                f"Searching for service with public_id: {public_id} for seller: {seller_id}"
            )

            query = (
                select(Service)
                .join(Service.peer)
                .where(Service.seller_id == seller_id, Peer.public_id == public_id)
                .options(
                    joinedload(Service.peer),
                    joinedload(Service.tariff),
                    joinedload(Service.interface),
                )
            )

            result = await self.session.execute(query)
            service = result.scalar_one_or_none()

            if service:
                logging.info(f"Found service with public_id: {public_id}")
            else:
                logging.info(f"No service found with public_id: {public_id}")

            return service

        except SQLAlchemyError as e:
            logging.error(
                f"Database error while searching service by public_id {public_id}: {str(e)}",
                exc_info=True,
            )
            raise

        except Exception as e:
            logging.error(
                f"Unexpected error while searching service by public_id {public_id}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_service_by_ip(self, seller_id: int, ip: str) -> Optional[Service]:
        """
        Get service by exact IP match for a specific seller.

        Args:
            seller_id: The ID of the seller
            ip: The IP address to search for

        Returns:
            Service object if found, None otherwise

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            logging.debug(
                f"Searching for service with IP: {ip} for seller: {seller_id}"
            )

            query = (
                select(Service)
                .join(Service.peer)
                .where(Service.seller_id == seller_id, Peer.allocated_ip == ip)
                .options(
                    joinedload(Service.peer),
                    joinedload(Service.tariff),
                    joinedload(Service.interface),
                )
            )

            result = await self.session.execute(query)
            service = result.scalar_one_or_none()

            if service:
                logging.info(f"Found service with IP: {ip}")
            else:
                logging.info(f"No service found with IP: {ip}")

            return service

        except SQLAlchemyError as e:
            logging.error(
                f"Database error while searching service by IP {ip}: {str(e)}",
                exc_info=True,
            )
            raise

        except Exception as e:
            logging.error(
                f"Unexpected error while searching service by IP {ip}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_inactive_services_with_peers(self) -> List[Service]:
        """
        Get inactive services with their associated peers.
        These are services that have been purchased but not yet activated by the user.
        """
        try:
            query = (
                select(Service)
                .where(
                    Service.status == ServiceStatus.UNUSED, Service.peer_id.is_not(None)
                )
                .options(
                    selectinload(Service.peer),
                    selectinload(Service.interface),
                    selectinload(Service.tariff),
                    selectinload(Service.seller),
                )
            )

            result = await self.session.execute(query)
            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logging.error(
                f"Database error in get_inactive_services_with_peers: {str(e)}"
            )
            raise

    async def get_active_services_with_peers(self) -> List[Service]:
        """
        Get active services with their associated peers.
        These are services that are currently active and need usage tracking.
        """
        try:
            query = (
                select(Service)
                .where(
                    Service.status == ServiceStatus.ACTIVE, Service.peer_id.is_not(None)
                )
                .options(
                    selectinload(Service.peer),
                    selectinload(Service.interface),
                    selectinload(Service.tariff),
                    selectinload(Service.seller),
                )
            )

            result = await self.session.execute(query)
            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logging.error(f"Database error in get_active_services_with_peers: {str(e)}")
            raise

    async def get_expired_services(self) -> List[Service]:
        """
        Get services that have expired but are still active.
        """
        try:
            now = datetime.now()

            query = (
                select(Service)
                .where(
                    Service.status == ServiceStatus.ACTIVE,
                    Service.expiry_date <= now,
                    Service.peer_id.is_not(None),
                )
                .options(
                    selectinload(Service.peer),
                    selectinload(Service.interface),
                    selectinload(Service.tariff),
                    selectinload(Service.seller),
                )
            )

            result = await self.session.execute(query)
            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logging.error(f"Database error in get_expired_services: {str(e)}")
            raise

    async def update_service(self, service_id: UUID, **kwargs) -> bool:
        """
        Update service with the provided fields.
        """
        try:
            stmt = update(Service).where(Service.id == service_id).values(**kwargs)

            await self.session.execute(stmt)
            await self.session.commit()
            return True

        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Database error in update_service: {str(e)}")
            raise

    async def update_service_usage(
        self,
        service_id: UUID,
        last_handshake: Optional[datetime] = None,
        download_bytes: Optional[int] = None,
        upload_bytes: Optional[int] = None,
        total_bytes: Optional[int] = None,
    ) -> bool:
        """
        Update service usage metrics.
        """
        try:
            update_values = {}

            if last_handshake is not None:
                update_values["last_handshake"] = last_handshake

            if download_bytes is not None:
                update_values["download_bytes"] = download_bytes

            if upload_bytes is not None:
                update_values["upload_bytes"] = upload_bytes

            if total_bytes is not None:
                update_values["total_bytes"] = total_bytes

            if not update_values:
                return False

            stmt = (
                update(Service).where(Service.id == service_id).values(**update_values)
            )

            await self.session.execute(stmt)
            await self.session.commit()
            return True

        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Database error in update_service_usage: {str(e)}")
            raise

    async def get_services_past_deletion_date(self) -> list[Service]:
        """
        Get services that have passed their deletion date and are in EXPIRED status.
        """
        try:
            stmt = (
                select(Service)
                .options(
                    selectinload(Service.seller),
                    selectinload(Service.tariff),
                    selectinload(Service.interface).selectinload(Interface.router),
                    selectinload(Service.peer),
                )
                .where(
                    and_(
                        Service.status == ServiceStatus.EXPIRED,
                        Service.deletion_date < datetime.now(),
                    )
                )
            )

            result = await self.session.execute(stmt)
            services = result.scalars().all()
            return list(services)

        except SQLAlchemyError as e:
            logging.error(
                f"Database error in get_services_past_deletion_date: {str(e)}"
            )
            raise
