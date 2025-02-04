from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.referrals import ReferralRepo
from infrastructure.database.repo.sellers import SellerRepo


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
    def referrals(self) -> ReferralRepo:
        """
        The Referral repository sessions are required to manage referral operations.
        """
        return ReferralRepo(self.session)
