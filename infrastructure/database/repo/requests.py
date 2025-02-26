# infrastructure/database/repo/requests.py
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.countries import CountryRepo
from infrastructure.database.repo.interfaces import InterfaceRepo
from infrastructure.database.repo.peers import PeerRepo
from infrastructure.database.repo.routers import RouterRepo
from infrastructure.database.repo.sellers import SellerRepo
from infrastructure.database.repo.services import ServiceRepo
from infrastructure.database.repo.tariffs import TariffRepo
from infrastructure.database.repo.transactions import TransactionRepo


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

    @property
    def interfaces(self) -> InterfaceRepo:
        return InterfaceRepo(self.session)

    @property
    def services(self) -> ServiceRepo:
        return ServiceRepo(self.session)

    @property
    def peers(self) -> PeerRepo:
        return PeerRepo(self.session)

    @property
    def transactions(self) -> TransactionRepo:
        return TransactionRepo(self.session)

    @property
    def routers(self) -> RouterRepo:
        return RouterRepo(self.session)
