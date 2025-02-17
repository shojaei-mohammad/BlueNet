import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import insert, update
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

    async def update_peer_keys(
        self, peer_id: UUID, private_key: str, public_key: str, config_file: str
    ) -> bool:
        """
        Update a peer's keys and config.

        Args:
            peer_id: UUID of the peer to update
            private_key: New private key
            public_key: New public key
            config_file: New config file content

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            stmt = (
                update(Peer)
                .where(Peer.id == peer_id)
                .values(
                    private_key=private_key,
                    public_key=public_key,
                    config_file=config_file,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0),
                )
                .returning(Peer.id)
            )

            result = await self.session.execute(stmt)
            await self.session.commit()

            return result.scalar_one_or_none() is not None

        except Exception as e:
            await self.session.rollback()
            logging.error(f"Error updating peer keys: {e}", exc_info=True)
            raise
