import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from infrastructure.database.models import ReferralLink
from infrastructure.database.repo.base import BaseRepo


class ReferralRepo(BaseRepo):
    async def verify_referral_link(self, referral_code: str) -> bool:
        """
        Verify if a referral link is valid and not expired.

        Args:
            referral_code: The referral code to verify

        Returns:
            bool: True if the link is valid and not expired, False otherwise
        """
        try:
            current_time = datetime.now(timezone.utc).replace(microsecond=0)
            query = select(ReferralLink).where(
                ReferralLink.code == referral_code,
                ReferralLink.is_active.is_(True),
                ReferralLink.expires_at > current_time,
            )

            result = await self.session.execute(query)
            link = result.scalar_one_or_none()

            if not link:
                return False

            # If the link has a max_uses limit, check if it's reached
            if link.max_uses is not None:
                if link.used_count >= link.max_uses:
                    link.is_active = False
                    await self.session.commit()
                    return False

            # Increment the used_count
            link.used_count += 1
            await self.session.commit()

            return True

        except Exception as e:
            logging.error(f"Error verifying referral link: {e}")
            return False

    async def create_referral_link(
        self,
        seller_id: UUID,
        code: str,
        expires_in_minutes: int,
        max_uses: Optional[int] = None,
    ) -> ReferralLink:
        """
        Create a new referral link for a seller

        Args:
            seller_id: ID of the seller creating the link
            code: Unique referral code
            expires_in_minutes: Number of minutes until expiration
            max_uses: Maximum number of times the link can be used (None for unlimited)

        Returns:
            ReferralLink: The created referral link object
        """
        expires_at = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(
            minutes=expires_in_minutes
        )

        new_link = ReferralLink(
            code=code,
            created_by=seller_id,
            expires_at=expires_at,
            max_uses=max_uses if max_uses > 0 else None,
            is_active=True,
            used_count=0,
        )

        self.session.add(new_link)
        await self.session.commit()
        await self.session.refresh(new_link)

        return new_link
