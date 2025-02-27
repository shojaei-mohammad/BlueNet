# infrastructure/database/repo/interfaces.py
import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func, Float, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from infrastructure.database.models import Interface, ServiceType, Router
from infrastructure.database.repo.base import BaseRepo


class InterfaceRepo(BaseRepo):
    async def get_available_interface(
        self, service_type: ServiceType, country_code: Optional[str] = None
    ) -> Optional[Interface]:
        """
        Get the least loaded available interface based on peer ratio.

        Args:
            service_type: Type of service (FIXED or DYNAMIC)
            country_code: Optional country code for fixed IPs

        Returns:
            Interface with the lowest current_peers/max_peers ratio or None if none available
        """
        try:
            # Calculate load ratio as a float
            load_ratio = func.cast(Interface.current_peers, Float) / func.cast(
                Interface.max_peers, Float
            )

            # Build base query
            query = (
                select(Interface)
                .options(selectinload(Interface.router))
                .where(
                    Interface.is_active.is_(True),
                    Interface.service_type == service_type,
                    Interface.current_peers < Interface.max_peers,
                )
                # Order by load ratio ascending (the least loaded first)
                .order_by(load_ratio)
                # Limit to 1 to get only the least loaded interface
                .limit(1)
            )

            # Add country code filter if specified
            if country_code:
                query = query.where(Interface.country_code == country_code)

            result = await self.session.execute(query)
            interface = result.scalar_one_or_none()

            if interface:
                # Log the selected interface details
                load_percentage = (interface.current_peers / interface.max_peers) * 100
                logging.info(
                    f"Selected interface {interface.interface_name} with "
                    f"load {load_percentage:.1f}% "
                    f"({interface.current_peers}/{interface.max_peers} peers)"
                )
            else:
                logging.warning(
                    f"No available interface found for service_type={service_type}, "
                    f"country_code={country_code}"
                )

            return interface

        except Exception as e:
            logging.error(f"Error finding available interface: {e}")
            raise

    async def increment_interface_counter(self, interface_id: UUID):
        """
        Increment the counter of the specified interface and its router.
        """
        try:
            # First, get the router_id for this interface
            result = await self.session.execute(
                select(Interface.router_id).where(Interface.id == interface_id)
            )
            router_id = result.scalar_one()

            # Update interface counter
            interface_stmt = (
                update(Interface)
                .where(Interface.id == interface_id)
                .values(
                    current_peers=Interface.current_peers + 1,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
            )
            await self.session.execute(interface_stmt)

            # Update router counter
            router_stmt = (
                update(Router)
                .where(Router.id == router_id)
                .values(
                    current_peers=Router.current_peers + 1,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
            )
            await self.session.execute(router_stmt)

            # Commit both updates
            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            logging.error(f"Error incrementing interface and router counters: {e}")
            raise

    async def decrement_interface_counter(self, interface_id: UUID):
        """
        Decrement the counter of the specified interface and its router.
        """
        try:
            # First, get the router_id for this interface
            result = await self.session.execute(
                select(Interface.router_id).where(Interface.id == interface_id)
            )
            router_id = result.scalar_one()

            # Update interface counter, ensuring it doesn't go below 0
            interface_stmt = (
                update(Interface)
                .where(Interface.id == interface_id, Interface.current_peers > 0)
                .values(
                    current_peers=Interface.current_peers - 1,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
            )
            await self.session.execute(interface_stmt)

            # Update router counter, ensuring it doesn't go below 0
            router_stmt = (
                update(Router)
                .where(Router.id == router_id, Router.current_peers > 0)
                .values(
                    current_peers=Router.current_peers - 1,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
            )
            await self.session.execute(router_stmt)

            # Commit both updates
            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            logging.error(f"Error decrementing interface and router counters: {e}")
            raise

    async def get_active_interfaces(self) -> List[Interface]:
        """
        Get all active interfaces with their router information.
        """
        try:
            query = (
                select(Interface)
                .where(Interface.is_active.is_(True))
                .options(selectinload(Interface.router))
            )

            result = await self.session.execute(query)
            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logging.error(f"Database error in get_active_interfaces: {str(e)}")
            raise
