# infrastructure/database/repo/sellers.py
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

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
