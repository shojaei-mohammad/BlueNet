# infrastructure/database/repo/routers.py
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import update, select

from infrastructure.database.models import Router, Interface
from infrastructure.database.repo.base import BaseRepo


class RouterRepo(BaseRepo):

    async def increment_router_counter(self, router_id: UUID):
        """
        Increment the counter of the specified router.
        """
        try:
            stmt = (
                update(Router)
                .where(Router.id == router_id)
                .values(
                    current_peers=Router.current_peers + 1,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
            )
            await self.session.execute(stmt)
            await self.session.commit()

        except Exception as e:
            logging.error(f"Error incrementing router counter: {e}")
            raise

    async def get_all_routers(self):
        """
        Get all routers from the database.

        Returns:
            List[Router]: List of all routers
        """
        try:
            result = await self.session.execute(select(Router))
            return result.scalars().all()
        except Exception as e:
            logging.error(f"Error getting all routers: {e}")
            raise

    async def update_router_status(self, router_id: UUID, is_active: bool):
        """
        Update a router's active status.

        Args:
            router_id: UUID of the router
            is_active: New status value
        """
        try:
            stmt = (
                update(Router)
                .where(Router.id == router_id)
                .values(
                    is_active=is_active,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
            )
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logging.error(f"Error updating router status: {e}")
            raise

    async def get_interfaces_by_router_id(self, router_id: UUID):
        """
        Get all interfaces for a specific router.

        Args:
            router_id: UUID of the router

        Returns:
            List[Interface]: List of interfaces
        """
        try:
            result = await self.session.execute(
                select(Interface).where(Interface.router_id == router_id)
            )
            return result.scalars().all()
        except Exception as e:
            logging.error(f"Error getting interfaces by router ID: {e}")
            raise
