# country_repo.py
import logging

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound, SQLAlchemyError

from infrastructure.database.models import Country
from infrastructure.database.repo.base import BaseRepo


class CountryRepo(BaseRepo):
    async def get_all_countries(self) -> list[Country]:
        try:
            logging.info("Fetching all countries")
            stmt = select(Country)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except NoResultFound as e:
            logging.error("No countries found", exc_info=True)
            raise Exception("No countries found") from e
        except SQLAlchemyError as e:
            logging.error(f"Failed to fetch countries: {e}", exc_info=True)
            raise Exception("Failed to fetch countries") from e
        except Exception as e:
            await self.session.rollback()
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
            raise Exception(
                "An unexpected error occurred during database operations."
            ) from e
