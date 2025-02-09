from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.countries import CountryRepo
from infrastructure.database.repo.sellers import SellerRepo
from infrastructure.database.repo.tariffs import TariffRepo


@dataclass
class RequestsRepo:
    """
    Repository for handling database operations. This class holds all the repositories for the database models.

    You can add more repositories as properties to this class, so they will be easily accessible.
    """

    session: AsyncSession

    @property
    def sellers(self) -> SellerRepo:
        """
        The User repository sessions are required to manage user operations.
        """
        return SellerRepo(self.session)

    @property
    def tariffs(self) -> TariffRepo:
        return TariffRepo(self.session)

    @property
    def countries(self) -> CountryRepo:
        return CountryRepo(self.session)
