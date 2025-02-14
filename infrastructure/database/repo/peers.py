import logging

from sqlalchemy import insert
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import Peer
from infrastructure.database.repo.base import BaseRepo


class PeerRepo(BaseRepo):
    async def create_peer(self, peer: Peer):
        try:
            # Extract data from the SQLAlchemy model into a dictionary
            peer_data = {
                "public_id": peer.public_id,
                "private_key": peer.private_key,
                "public_key": peer.public_key,
                "allocated_ip": peer.allocated_ip,
                "dns_servers": peer.dns_servers,
                "end_point": peer.end_point,
                "config_file": peer.config_file,
                "peer_comment": peer.peer_comment,
            }

            # Create the insert statement
            insert_stmt = insert(Peer).values(**peer_data).returning(Peer)

            # Execute the statement
            result = await self.session.execute(insert_stmt)
            await self.session.commit()

            # Return the inserted record
            return result.scalar_one()

        except SQLAlchemyError as e:
            await self.session.rollback()
            logging.error(f"Failed to create peer: {e}")
            raise Exception("Failed to create peer in the database.") from e

        except Exception as e:
            await self.session.rollback()
            logging.error(f"An unexpected error occurred: {e}")
            raise Exception(
                "An unexpected error occurred during database operations."
            ) from e
