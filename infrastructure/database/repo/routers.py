# infrastructure/database/repo/interfaces.py
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import update

from infrastructure.database.models import Interface, Router
from infrastructure.database.repo.base import BaseRepo


class RouterRepo(BaseRepo):

    async def increment_router_counter(self, router_id: UUID):
        """
        Increment the counter of the specified interface.
        """
        try:
            stmt = (
                update(Router)
                .where(Router.id == router_id)
                .values(
                    current_peers=Interface.current_peers + 1,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
            )
            await self.session.execute(stmt)
            await self.session.commit()

        except Exception as e:
            logging.error(f"Error incrementing interface counter: {e}")
            raise
