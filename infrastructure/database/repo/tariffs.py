# tariff_repo.py
import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, NoResultFound

from infrastructure.database.models import Tariff, ServiceType
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class TariffRepo(BaseRepo):
    async def get_tariffs_by_service_type(
        self, service_type: ServiceType
    ) -> list[Tariff]:
        try:
            logging.info(f"Fetching tariffs for service type: {service_type}")
            stmt = select(Tariff).where(Tariff.service_type == service_type)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except NoResultFound as e:
            logging.error(
                f"No tariffs found for service type: {service_type}", exc_info=True
            )
            raise Exception(f"No tariffs found for service type: {service_type}") from e
        except SQLAlchemyError as e:
            logging.error(
                f"Failed to fetch tariffs for service type: {service_type}: {e}",
                exc_info=True,
            )
            raise Exception(
                f"Failed to fetch tariffs for service type: {service_type}"
            ) from e
        except Exception as e:
            await self.session.rollback()
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
            raise Exception(
                "An unexpected error occurred during database operations."
            ) from e
