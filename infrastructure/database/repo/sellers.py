import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.sellers import (
    Seller,
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
