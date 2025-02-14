# infrastructure/database/repo/services.py
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import insert, update
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import Service
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
