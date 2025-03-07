# infrastructure/database/repo/sellers.py
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple, List, Dict

from sqlalchemy import update, select, func, and_, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import ServiceStatus, Service
from infrastructure.database.models.sellers import (
    Seller,
    SellerStatus,
)
from infrastructure.database.repo.base import BaseRepo


class SellerRepo(BaseRepo):
    async def get_or_create_seller(
        self,
        chat_id: int,
        username: str | None = None,
        full_name: str | None = None,
    ) -> Seller:
        """
        Creates or updates a seller in the database and returns the seller object.
        Only fields provided as parameters will be updated in the case of a conflict.

        Args:
            chat_id: Telegram chat ID of the seller
            username: Telegram username
            full_name: Full name of the seller

        Returns:
            Seller: Created or updated seller object

        Raises:
            Exception: If database operation fails
        """
        values_dict = {
            "chat_id": chat_id,
            "username": username,
            "full_name": full_name,
        }

        try:
            insert_stmt = (
                insert(Seller)
                .values(**values_dict)
                .on_conflict_do_update(
                    index_elements=[Seller.chat_id],
                    set_={
                        key: values_dict[key] for key in values_dict if key != "chat_id"
                    },
                )
                .returning(Seller)
            )

            result = await self.session.execute(insert_stmt)
            await self.session.commit()
            return result.scalar_one()

        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Failed to insert or update seller: {e}")
            raise Exception("Failed to insert or update seller in the database.") from e

        except Exception as e:
            await self.session.rollback()
            logging.error(f"An unexpected error occurred: {e}")
            raise Exception(
                "An unexpected error occurred during database operations."
            ) from e

    async def update_seller_status(
        self, seller_id: int, status: SellerStatus, is_active: bool = False
    ) -> Seller:
        try:
            stmt = (
                update(Seller)
                .where(Seller.id == seller_id)
                .values(
                    status=status,
                    is_active=is_active,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
                .returning(Seller)
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.scalar_one()
        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Failed to update seller status: {e}")
            raise

    async def complete_seller_registration(
        self,
        seller_id: int,
        discount_percent: Decimal,
        debt_limit: Decimal,
        status: SellerStatus = SellerStatus.APPROVED,
    ) -> Seller:
        try:
            stmt = (
                update(Seller)
                .where(Seller.id == seller_id)
                .values(
                    discount_percent=discount_percent,
                    debt_limit=debt_limit,
                    status=status,
                    is_active=True,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
                .returning(Seller)
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.scalar_one()
        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Failed to complete seller registration: {e}")
            raise

    async def update_seller_dept(
        self, seller_id: int, seller_price: Decimal, profit: Decimal
    ) -> Seller:
        try:
            stmt = (
                update(Seller)
                .where(Seller.id == seller_id)
                .values(
                    current_debt=Seller.current_debt + seller_price,
                    total_sale=Seller.total_sale + (seller_price + profit),
                    total_profit=Seller.total_profit + profit,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
                .returning(Seller)
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.scalar_one()
        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Failed to update seller status: {e}")
            raise

    async def get_seller_by_id(self, seller_id: int) -> Optional[Seller]:
        """
        Get a seller by their ID.

        Args:
            seller_id: The ID of the seller to retrieve

        Returns:
            Optional[Seller]: The seller if found, None otherwise
        """
        try:
            stmt = select(Seller).where(Seller.id == seller_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logging.error(f"Failed to get seller by ID: {e}")
            raise

    async def get_all_chat_ids(self):
        try:
            stmt = select(Seller.chat_id)
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logging.error(f"Failed to get users chat id: {e}")
            raise

    async def get_paginated_sellers(
        self, page: int = 1, per_page: int = 10
    ) -> Tuple[List[Seller], int]:
        """
        Get paginated list of sellers with their total count

        Args:
            page: Page number (starting from 1)
            per_page: Number of sellers per page

        Returns:
            Tuple of (list of sellers, total count)
        """
        # Calculate offset
        offset = (page - 1) * per_page

        # Query for sellers with pagination
        query = select(Seller).order_by(Seller.created_at.desc())
        paginated_query = query.offset(offset).limit(per_page)

        # Execute queries
        result = await self.session.execute(paginated_query)
        sellers = list(result.scalars().all())

        # Get total count
        count_query = select(func.count()).select_from(Seller)
        count_result = await self.session.execute(count_query)
        total_count = count_result.scalar()

        return sellers, total_count

    async def get_seller_with_service_stats(
        self, seller_id: int
    ) -> Tuple[Optional[Seller], Dict[ServiceStatus, int]]:
        """
        Get seller details along with counts of their services by status

        Args:
            seller_id: ID of the seller

        Returns:
            Tuple of (seller object, dictionary of service counts by status)
        """
        # Get seller
        seller_query = select(Seller).where(Seller.id == seller_id)
        result = await self.session.execute(seller_query)
        seller = result.scalars().first()

        if not seller:
            return None, {}

        # Get service counts by status
        stats = {}
        for status in ServiceStatus:
            count_query = (
                select(func.count())
                .select_from(Service)
                .where(and_(Service.seller_id == seller_id, Service.status == status))
            )
            count_result = await self.session.execute(count_query)
            stats[status] = count_result.scalar() or 0

        return seller, stats

    async def update_seller_discount_and_debt_limit(
        self,
        seller_id: int,
        discount_percent: Decimal = None,
        debt_limit: Decimal = None,
    ) -> Optional[Seller]:
        """
        Update seller discount percentage and/or debt limit

        Args:
            seller_id: ID of the seller
            discount_percent: New discount percentage (0-100)
            debt_limit: New debt limit

        Returns:
            Updated seller object or None if not found
        """
        # Get seller
        seller_query = select(Seller).where(Seller.id == seller_id)
        result = await self.session.execute(seller_query)
        seller = result.scalars().first()

        if not seller:
            return None

        # Update fields
        if discount_percent is not None:
            seller.discount_percent = discount_percent

        if debt_limit is not None:
            seller.debt_limit = debt_limit

        await self.session.commit()
        await self.session.refresh(seller)
        return seller

    async def search_sellers(self, query: str) -> List[Seller]:
        """
        Search for sellers by username or full name

        Args:
            query: Search query string

        Returns:
            List of matching sellers
        """
        # Prepare search query with case-insensitive matching
        search_query = (
            select(Seller)
            .where(
                or_(
                    Seller.username.ilike(f"%{query}%"),
                    Seller.full_name.ilike(f"%{query}%"),
                )
            )
            .order_by(Seller.created_at.desc())
        )

        # Execute query
        result = await self.session.execute(search_query)
        return list(result.scalars().all())
