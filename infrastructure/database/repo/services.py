# infrastructure/database/repo/services.py
import logging
from datetime import datetime, timezone
from typing import Tuple, List, Optional
from uuid import UUID

from sqlalchemy import insert, update, select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload

from infrastructure.database.models import Service, Peer, ServiceStatus
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
        Get a service by its ID with related peer information.

        Args:
            service_id: The ID of the service to retrieve

        Returns:
            Service object if found, None otherwise
        """
        try:
            # Create query joining Service with Peer
            query = (
                select(Service)
                .outerjoin(Peer)
                .options(selectinload(Service.peer))  # Eager load peer relationship
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
                .values(status=new_status)
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
