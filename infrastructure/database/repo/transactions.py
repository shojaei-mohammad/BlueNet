# infrastructure/database/repo/transactions.py
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import insert, select, delete, and_, desc, update
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import Transaction
from infrastructure.database.repo.base import BaseRepo


class TransactionRepo(BaseRepo):
    async def create_transaction(self, transaction: Transaction):
        try:
            # Extract data from the SQLAlchemy model into a dictionary
            transaction_data = {
                "seller_id": transaction.seller_id,
                "service_id": transaction.service_id,
                "amount": transaction.amount,
                "transaction_type": transaction.transaction_type,
                "description": transaction.description,
            }

            # Create the insert statement
            insert_stmt = (
                insert(Transaction).values(**transaction_data).returning(Transaction)
            )

            # Execute the statement
            result = await self.session.execute(insert_stmt)
            await self.session.commit()

            # Return the inserted record
            return result.scalar_one()

        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Failed to create transaction: {e}")
            raise Exception("Failed to create transaction in the database.") from e

        except Exception as e:
            await self.session.rollback()
            logging.error(f"An unexpected error occurred: {e}")
            raise Exception(
                "An unexpected error occurred during database operations."
            ) from e

    async def get_transaction(self, transaction_id: UUID) -> Optional[Transaction]:
        """Get transaction by ID."""
        try:
            stmt = select(Transaction).where(Transaction.id == transaction_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logging.error(f"Failed to get transaction: {e}")
            raise Exception("Failed to create transaction in the database.") from e

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            raise Exception(
                "An unexpected error occurred during database operations."
            ) from e

    async def delete_transaction(self, transaction_id: UUID) -> bool:
        """Delete transaction by ID."""
        try:
            stmt = delete(Transaction).where(Transaction.id == transaction_id)
            await self.session.execute(stmt)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Failed to delete transaction: {e}")
            raise

    async def get_seller_transactions_paginated(
        self, seller_id: int, days: int = 30, page: int = 1, page_size: int = 5
    ) -> tuple[list[Transaction], int]:
        """
        Get paginated transactions for a seller within the specified number of days.

        Args:
            seller_id: ID of the seller
            days: Number of days to look back (default: 30)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (list of transactions, total count)
        """
        try:
            # Calculate the date threshold
            date_threshold = datetime.now() - timedelta(days=days)

            # Count total matching transactions
            count_stmt = select(Transaction).where(
                and_(
                    Transaction.seller_id == seller_id,
                    Transaction.created_at >= date_threshold,
                )
            )
            count_result = await self.session.execute(count_stmt)
            total_count = len(count_result.scalars().all())

            # Get paginated results
            offset = (page - 1) * page_size

            stmt = (
                select(Transaction)
                .where(
                    and_(
                        Transaction.seller_id == seller_id,
                        Transaction.created_at >= date_threshold,
                    )
                )
                .order_by(desc(Transaction.created_at))
                .offset(offset)
                .limit(page_size)
            )

            result = await self.session.execute(stmt)
            transactions = result.scalars().all()

            return list(transactions), total_count

        except SQLAlchemyError as e:
            logging.error(
                f"Database error in get_seller_transactions_paginated: {str(e)}"
            )
            raise

    async def update_transaction_proof(self, transaction_id: UUID, proof: str) -> None:

        try:
            stmt = (
                update(Transaction)
                .where(Transaction.id == transaction_id)
                .values(proof=proof)
            )
            await self.session.execute(stmt)
            await self.session.commit()

        except SQLAlchemyError as e:
            logging.error(
                f"Database error in get_seller_transactions_paginated: {str(e)}"
            )
            raise
