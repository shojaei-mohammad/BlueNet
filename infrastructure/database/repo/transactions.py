# infrastructure/database/repo/transactions.py
import logging

from sqlalchemy import insert
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
