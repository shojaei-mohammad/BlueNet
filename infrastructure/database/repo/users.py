import logging
from typing import Optional

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import BotUser
from infrastructure.database.repo.base import BaseRepo


class UserRepo(BaseRepo):
    async def get_or_create_user(
        self,
        chat_id: int,
        name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        referral_code: Optional[int] = None,
        referred_by: Optional[int] = None,
        referral_count: int = 0,
        referral_link: Optional[str] = None,
        pref_language: Optional[str] = None,
    ):
        """
        Creates or updates a new user in the database and returns the user object.
        Only fields provided as parameters will be updated in the case of a conflict.
        """

        values_dict = {
            "ChatID": chat_id,
            "Name": name,
            "Lastname": last_name,
            "Username": username,
            "ReferralCode": referral_code,
            "ReferredBy": referred_by,
            "ReferralCount": referral_count,
            "ReferralLink": referral_link,
            "PrefLanguage": pref_language,
        }

        # Remove None values to avoid nullifying columns in the database
        values_dict = {
            key: value for key, value in values_dict.items() if value is not None
        }

        try:
            insert_stmt = (
                insert(BotUser)
                .values(**values_dict)
                .on_conflict_do_update(
                    index_elements=[BotUser.ChatID],
                    set_={
                        key: values_dict[key] for key in values_dict if key != "ChatID"
                    },
                )
                .returning(BotUser)
            )

            result = await self.session.execute(insert_stmt)
            await self.session.commit()
            return result.scalar_one()
        except SQLAlchemyError as e:
            await self.session.rollback()
            # Log the error or re-raise with additional information if necessary
            logging.error(f"Failed to insert or update user: {e}")
            raise Exception("Failed to insert or update user in the database.") from e
        except Exception as e:
            await self.session.rollback()
            # Handle other exceptions, possibly re-raise
            logging.error(f"An unexpected error occurred: {e}")
            raise Exception(
                "An unexpected error occurred during database operations."
            ) from e

    async def update_referral_count(self, referrer_chat_id: int):
        try:
            # Start a transaction explicitly to handle multistep operations safely
            async with self.session.begin():
                stmt = (
                    update(BotUser)
                    .values(ReferralCount=BotUser.ReferralCount + 1)
                    .where(BotUser.ChatID == referrer_chat_id)
                )
                result = await self.session.execute(stmt)

                # Check if the update has affected any rows
                if result.rowcount == 0:
                    logging.warning(
                        f"No referrer found with ChatID {referrer_chat_id} to update."
                    )
                    return  # Early exit if no rows are updated

                # Refresh the referrer instance to reflect updated values
                referrer = await self.session.get(BotUser, referrer_chat_id)
                if referrer:
                    await self.session.refresh(referrer)
                    logging.info(
                        f"Referrer data updated for ChatID {referrer_chat_id}. "
                        f"Referral count is now {referrer.ReferralCount}."
                    )

        except Exception as e:
            logging.error(
                f"Failed to update referrer data for ChatID {referrer_chat_id}: {e}"
            )
            raise Exception(
                "An unexpected error occurred during database operations."
            ) from e

    async def update_referred_by(self, chat_id: int, referrer_chat_id: int):
        try:
            stmt = (
                update(BotUser)
                .values(ReferredBy=referrer_chat_id)
                .where(BotUser.ChatID == chat_id)
            )
            result = await self.session.execute(stmt)
            if result.rowcount:
                logging.info(
                    f"Updated referrer for user {chat_id} to {referrer_chat_id}"
                )
            else:
                logging.warning(
                    f"No user found with ChatID {chat_id} to update referrer."
                )

            await self.session.commit()
        except Exception as e:
            logging.error(f"Failed to update referrer for user {chat_id}: {e}")
            await self.session.rollback()  # Roll back in case of an error
            raise
