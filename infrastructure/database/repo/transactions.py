# infrastructure/database/repo/transactions.py
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import insert, select, delete
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
