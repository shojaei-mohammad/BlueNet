# tariff_repo.py
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, NoResultFound

from infrastructure.database.models import Tariff, ServiceType
from infrastructure.database.repo.base import BaseRepo


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

    async def get_tariffs_by_country_code(self, country_code: str) -> list[Tariff]:
        try:
            logging.info(f"Fetching tariffs for country code: {country_code}")
            stmt = select(Tariff).where(Tariff.country_code == country_code)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except NoResultFound as e:
            logging.error(
                f"No tariffs found for country code: {country_code}", exc_info=True
            )
            raise Exception(f"No tariffs found for country code: {country_code}") from e
        except SQLAlchemyError as e:
            logging.error(
                f"Failed to fetch tariffs for country code: {country_code}: {e}",
                exc_info=True,
            )
            raise Exception(
                f"Failed to fetch tariffs for country code: {country_code}"
            ) from e
        except Exception as e:
            await self.session.rollback()
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
            raise Exception(
                "An unexpected error occurred during database operations."
            ) from e

    async def get_tariff_details(self, tariff_id: UUID):
        """
        Fetch tariff details for a given tariff ID.
        """
        try:
            logging.info(f"Fetching tariff details for tariff ID: {tariff_id}")
            stmt = select(Tariff).where(Tariff.id == tariff_id)
            result = await self.session.execute(stmt)
            tariff = result.scalars().first()  # Get the first result (or None)

            if tariff is None:
                raise NoResultFound(f"No tariff found for tariff ID: {tariff_id}")

            return tariff  # Return the single tariff object

        except NoResultFound as e:
            logging.error(f"No tariff found for tariff ID: {tariff_id}", exc_info=True)
            raise Exception(f"No tariff found for tariff ID: {tariff_id}") from e

        except SQLAlchemyError as e:
            logging.error(
                f"Failed to fetch tariff details for tariff ID: {tariff_id}: {e}",
                exc_info=True,
            )
            raise Exception(
                f"Failed to fetch tariff details for tariff ID: {tariff_id}"
            ) from e

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
            raise Exception(
                "An unexpected error occurred during database operations."
            ) from e

    async def get_compatible_tariffs(
        self, service_type: ServiceType, country_code: str
    ) -> list[Tariff]:
        """
        Fetch tariffs that are compatible with the given service type and country code.

        Args:
            service_type (ServiceType): The type of service
            country_code (str): The country code for the tariffs

        Returns:
            list[Tariff]: List of compatible tariffs

        Raises:
            Exception: If there's an error fetching the tariffs
        """
        try:
            logging.info(
                f"Fetching compatible tariffs for service_type: {service_type}, "
                f"country_code: {country_code}"
            )

            stmt = (
                select(Tariff)
                .where(
                    Tariff.service_type == service_type,
                    Tariff.country_code == country_code,
                )
                .order_by(Tariff.price)  # Order by price ascending
            )

            result = await self.session.execute(stmt)
            tariffs = list(result.scalars().all())

            if not tariffs:
                logging.warning(
                    f"No compatible tariffs found for service_type: {service_type}, "
                    f"country_code: {country_code}"
                )
                return []

            logging.info(f"Found {len(tariffs)} compatible tariffs")
            return tariffs

        except SQLAlchemyError as e:
            logging.error(
                f"Database error while fetching compatible tariffs: {e}", exc_info=True
            )
            raise Exception(
                "Failed to fetch compatible tariffs due to database error"
            ) from e
        except Exception as e:
            logging.error(
                f"Unexpected error while fetching compatible tariffs: {e}",
                exc_info=True,
            )
            raise Exception(
                "An unexpected error occurred while fetching compatible tariffs"
            ) from e
