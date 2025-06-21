import asyncio
import ipaddress
import logging
import subprocess
from typing import Dict, Any, Optional, Tuple

from routeros_api import RouterOsApiPool
from routeros_api.exceptions import (
    RouterOsApiConnectionError,
    RouterOsApiCommunicationError,
)

from tgbot.models.wireguard import WireguardConfig, PurchaseData, WireguardPeerConfig
from tgbot.services.utils import generate_qr_code


class WireguardManager:
    def __init__(self, config: WireguardConfig):
        self.config = config
        self._client_pool = None
        self._server_public_key = None
        self._max_retries = 3
        self._retry_delay = 2  # seconds

    async def _ensure_connected(self, force: bool = False):
        """Ensure connection to the MikroTik router."""
        if force or not self._client_pool:
            try:
                if self._client_pool:
                    self._client_pool.disconnect()
                self._client_pool = RouterOsApiPool(
                    host=self.config.router_host,
                    username=self.config.router_user,
                    password=self.config.router_password,
                    port=self.config.router_port,
                    plaintext_login=True,
                )
                logging.info("Initialized MikroTik router connection pool.")
            except Exception as e:
                logging.error(
                    f"Failed to initialize MikroTik router connection pool: {e}"
                )
                raise

    @staticmethod
    async def _generate_peer_comment(data: PurchaseData, ip_address: str) -> str:
        """Generate a unique peer comment."""
        last_octet = ip_address.split(".")[-1]
        return f"{data.interface_name}_{last_octet}_{data.seller_id}_{data.purchase_id}"

    async def _execute_api_command(self, func, *args, **kwargs):
        """Execute API command with retry logic."""
        for attempt in range(self._max_retries):
            try:
                return func(*args, **kwargs)  # Call the function directly
            except (RouterOsApiConnectionError, RouterOsApiCommunicationError) as e:
                if attempt == self._max_retries - 1:
                    raise
                logging.warning(
                    f"API command failed (attempt {attempt + 1}/{self._max_retries}): {e}"
                )
                await asyncio.sleep(self._retry_delay)
                await self._ensure_connected()  # Reconnect before retry

    async def _find_available_ip(self, api, subnet: str) -> str:
        """Find an available IP address in the given subnet."""
        try:
            # Get the Wireguard peers resource
            peer_resource = api.get_resource("/interface/wireguard/peers")

            # Get existing peers
            existing_peers = await self._execute_api_command(peer_resource.get)

            # Extract used IPs
            used_ips = set()
            for peer in existing_peers:
                if "allowed-address" in peer:
                    ip = peer["allowed-address"].split("/")[0]
                    used_ips.add(ip)

            # Generate network range
            network = ipaddress.ip_network(subnet)

            # Find first available IP
            for ip in network.hosts():
                ip_str = str(ip)
                if ip_str not in used_ips and ip_str.split(".")[3] != "1":
                    return ip_str

            raise ValueError(f"No available IPs in range {subnet}")

        except Exception as e:
            logging.error(f"Failed to find available IP: {e}")
            raise

    async def _add_peer(self, api, peer_config: WireguardPeerConfig) -> Dict[str, Any]:
        """Add a new WireGuard peer to the router."""
        try:
            logging.info(
                f"Adding new WireGuard peer with comment: {peer_config.comment}"
            )

            # Get the Wireguard peers resource
            peer_resource = api.get_resource("/interface/wireguard/peers")

            # Prepare peer configuration
            peer_data = {
                "interface": peer_config.interface_name,
                "public-key": peer_config.public_key,
                "allowed-address": f"{peer_config.allowed_ip}/32",
                "comment": peer_config.comment,
            }

            # Add the peer
            result = await self._execute_api_command(peer_resource.add, **peer_data)

            # Convert result to dictionary if needed
            if hasattr(result, "get"):
                result = result.get()
            elif isinstance(result, (list, tuple)) and len(result) > 0:
                result = result[0]
            else:
                result = {"ret": "ok"}

            logging.info(f"Successfully added WireGuard peer: {peer_config.comment}")
            return result

        except Exception as e:
            logging.error(f"Failed to add WireGuard peer: {e}")
            raise

    @staticmethod
    async def _generate_keypair() -> Tuple[str, str]:
        """Generate a WireGuard key pair."""
        try:
            # Generate private key
            private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()

            # Generate public key
            public_key = (
                subprocess.check_output(["wg", "pubkey"], input=private_key.encode())
                .decode()
                .strip()
            )

            return private_key, public_key

        except Exception as e:
            logging.error(f"Failed to generate keypair: {e}")
            raise

    async def _find_peer_by_comment(
        self, api, interface_name: str, comment: str
    ) -> Optional[Dict[str, Any]]:
        """Find a WireGuard peer by its comment."""
        try:
            # Get the Wireguard peers resource
            peer_resource = api.get_resource("/interface/wireguard/peers")

            # Get all peers
            peers = await self._execute_api_command(
                peer_resource.get
            )  # Remove api parameter

            # Filter peers manually
            matching_peers = [
                peer
                for peer in peers
                if peer.get("interface") == interface_name
                and peer.get("comment") == comment
            ]

            # Return the first matching peer or None
            return matching_peers[0] if matching_peers else None

        except Exception as e:
            logging.error(f"Failed to find peer by comment: {e}")
            return None

    @staticmethod
    async def _update_peer_status(
        api, interface_name: str, peer_id: str, disabled: bool
    ) -> bool:
        """Enable or disable a WireGuard peer."""
        try:
            # Get the Wireguard peers resource
            peer_resource = api.get_resource("/interface/wireguard/peers")

            # Log the current state before update
            current_state = peer_resource.get(id=peer_id)
            logging.info(f"Current peer state before update: {current_state}")

            # Update peer status
            update_params = {
                ".id": peer_id,
                "disabled": "true" if disabled else "false",
            }
            logging.info(f"Updating peer with parameters: {update_params}")

            peer_resource.set(**update_params)

            # Verify the new state
            new_state = peer_resource.get(id=peer_id)
            logging.info(f"New peer state after update: {new_state}")

            logging.info(
                f"Successfully {'disabled' if disabled else 'enabled'} "
                f"peer {peer_id} on interface {interface_name}"
            )
            return True

        except Exception as e:
            logging.error(f"Failed to update peer status: {e}")
            return False

    async def _delete_peer(self, api, interface_name: str, peer_id: str) -> bool:
        """Delete a WireGuard peer from the router."""
        try:
            # Get the Wireguard peers resource
            peer_resource = api.get_resource("/interface/wireguard/peers")

            # Delete the peer
            await self._execute_api_command(peer_resource.remove, id=peer_id)

            logging.info(
                f"Successfully deleted peer {peer_id} on interface {interface_name}"
            )
            return True

        except Exception as e:
            logging.error(f"Failed to delete peer: {e}")
            return False

    @staticmethod
    async def _generate_client_config(
        server_config: Dict[str, Any], client_config: WireguardPeerConfig
    ) -> str:
        """Generate a WireGuard client configuration."""
        try:
            config = [
                "[Interface]",
                f"PrivateKey = {client_config.private_key}",
                f"Address = {client_config.allowed_ip}/32",
                f"DNS = {server_config['dns_servers']}",
                "",
                "[Peer]",
                f"PublicKey = {server_config['public_key']}",
                f"AllowedIPs = {server_config['allowed_ips']}",
                f"Endpoint = {server_config['endpoint']}",
                f"PersistentKeepalive={25}",
            ]

            return "\n".join(config)

        except Exception as e:
            logging.error(f"Failed to generate client config: {e}")
            raise

    async def create_peer(
        self, interface_name: str, purchase_data: PurchaseData
    ) -> tuple[WireguardPeerConfig, str, bytes]:
        """
        Create a new WireGuard peer configuration.

        Args:
            interface_name: Name of the WireGuard interface
            purchase_data: Purchase data for peer identification

        Returns:
            Tuple of (WireguardPeerConfig, config_file, qr_code)
        """
        try:
            # Ensure connection to router
            await self._ensure_connected()
            api = self._client_pool.get_api()

            # Generate WireGuard keypair
            private_key, public_key = await self._generate_keypair()

            # Find available IP address
            available_ip = await self._find_available_ip(api, self.config.subnet)

            # Generate peer comment
            peer_comment = await self._generate_peer_comment(
                purchase_data, available_ip
            )

            # Create peer configuration object
            peer_config = WireguardPeerConfig(
                interface_name=interface_name,
                private_key=private_key,
                public_key=public_key,
                allowed_ip=available_ip,
                comment=peer_comment,
            )

            # Add peer to router
            await self._add_peer(api, peer_config)

            # Generate client configuration
            server_config = {
                "dns_servers": self.config.dns_servers,
                "public_key": self.config.public_key,
                "allowed_ips": self.config.allowed_ips,
                "endpoint": f"{self.config.endpoint}",
            }
            config_file = await self._generate_client_config(server_config, peer_config)

            # Generate QR code
            qr_code = await generate_qr_code(config_file)

            return peer_config, config_file, qr_code

        except Exception as e:
            logging.error(f"Failed to create WireGuard peer: {e}")
            raise

    async def disable_peer(self, interface_name: str, peer_comment: str) -> bool:
        """
        Disable a WireGuard peer on the router.

        Args:
            interface_name: Name of the WireGuard interface
            peer_comment: Comment/identifier of the peer to disable

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure connection to router
            await self._ensure_connected()
            api = self._client_pool.get_api()

            # Find the peer by comment
            peer = await self._find_peer_by_comment(api, interface_name, peer_comment)

            if not peer:
                logging.error(f"Peer not found: {peer_comment}")
                return False

            # Disable the peer
            success = await self._update_peer_status(
                api, interface_name, peer["id"], disabled=True
            )

            if success:
                logging.info(f"Successfully disabled peer: {peer_comment}")
                return True
            else:
                logging.error(f"Failed to disable peer: {peer_comment}")
                return False

        except Exception as e:
            logging.error(f"Error disabling peer {peer_comment}: {e}")
            return False
        finally:
            if self._client_pool:
                self._client_pool.disconnect()

    async def enable_peer(self, interface_name: str, peer_comment: str) -> bool:
        """
        Enable a WireGuard peer on the router.

        Args:
            interface_name: Name of the WireGuard interface
            peer_comment: Comment/identifier of the peer to enable

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure connection to router
            await self._ensure_connected()
            api = self._client_pool.get_api()

            # Find the peer by comment
            peer = await self._find_peer_by_comment(api, interface_name, peer_comment)

            if not peer:
                logging.error(f"Peer not found: {peer_comment}")
                return False

            # Enable the peer
            success = await self._update_peer_status(
                api, interface_name, peer["id"], disabled=False
            )

            if success:
                logging.info(f"Successfully enabled peer: {peer_comment}")
                return True
            else:
                logging.error(f"Failed to enable peer: {peer_comment}")
                return False

        except Exception as e:
            logging.error(f"Error enabling peer {peer_comment}: {e}")
            return False
        finally:
            if self._client_pool:
                self._client_pool.disconnect()

    async def reset_peer(
        self, interface_name: str, peer_comment: str
    ) -> Optional[Tuple[WireguardPeerConfig, str, bytes]]:
        """
        Reset a WireGuard peer's keys on the router.

        Args:
            interface_name: Name of the WireGuard interface
            peer_comment: Comment/identifier of the peer to reset

        Returns:
            Optional[Tuple[WireguardPeerConfig, str, str]]: (peer_config, config_file, qr_code) if successful, None otherwise
        """
        try:
            # Ensure connection to router
            await self._ensure_connected()
            api = self._client_pool.get_api()

            # Find the peer by comment
            peer = await self._find_peer_by_comment(api, interface_name, peer_comment)

            if not peer:
                logging.error(f"Peer not found: {peer_comment}")
                return None

            # Generate new WireGuard keypair
            private_key, public_key = await self._generate_keypair()

            # Create peer configuration object with existing IP but new keys
            peer_config = WireguardPeerConfig(
                interface_name=interface_name,
                private_key=private_key,
                public_key=public_key,
                allowed_ip=peer["allowed-address"].split("/")[0],
                comment=peer_comment,
            )

            # Update peer on router
            peer_resource = api.get_resource("/interface/wireguard/peers")
            await self._execute_api_command(
                peer_resource.set,
                **{
                    ".id": peer["id"],
                    "public-key": public_key,
                },
            )

            # Generate new client configuration
            server_config = {
                "dns_servers": self.config.dns_servers,
                "public_key": self.config.public_key,
                "allowed_ips": self.config.allowed_ips,
                "endpoint": f"{self.config.endpoint}",
            }
            config_file = await self._generate_client_config(server_config, peer_config)

            # Generate QR code
            qr_code = await generate_qr_code(config_file)

            logging.info(f"Successfully reset peer: {peer_comment}")
            return peer_config, config_file, qr_code

        except Exception as e:
            logging.error(f"Error resetting peer {peer_comment}: {e}")
            return None
        finally:
            if self._client_pool:
                self._client_pool.disconnect()

    async def test_connection(self) -> bool:
        """
        Test if connection to router API is working.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Use the existing _ensure_connected method to establish connection
            await self._ensure_connected()

            # If we get here without exception, try to execute a simple command
            api = self._client_pool.get_api()
            system_resource = api.get_resource("/system/resource")
            system_resource.get()

            return True
        except (RouterOsApiConnectionError, RouterOsApiCommunicationError) as e:
            logging.debug(f"Router connection test failed: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error in router connection test: {e}")
            return False
        finally:
            # Disconnect after test
            if self._client_pool:
                self._client_pool.disconnect()
                self._client_pool = None

    async def get_peer_handshake_status(
        self, interface_name: str, peer_comment: str
    ) -> tuple[bool, str]:
        """
        Check if a peer has an active handshake.

        Args:
            interface_name: Name of the WireGuard interface
            peer_comment: Comment/identifier of the peer

        Returns:
            Tuple of (is_active: bool, raw_handshake_value: str)
        """
        try:
            # Ensure connection to router
            await self._ensure_connected()
            api = self._client_pool.get_api()

            # Find the peer by comment
            peer = await self._find_peer_by_comment(api, interface_name, peer_comment)

            if not peer:
                logging.error(f"Peer not found: {peer_comment}")
                return False, ""

            # Get the raw handshake value
            handshake_time = peer.get("last-handshake", "")

            # Check if handshake indicates activity
            is_active = False
            if handshake_time:
                # If it's a numeric timestamp, check if it's greater than 0
                if handshake_time.isdigit():
                    is_active = int(handshake_time) > 0
                # If it's a time string like "1m4s", it indicates an active handshake
                elif (
                    "m" in handshake_time
                    or "s" in handshake_time
                    or "h" in handshake_time
                ):
                    is_active = True
                # Any other non-empty value suggests activity
                elif handshake_time != "0" and handshake_time.lower() != "never":
                    is_active = True

            return is_active, handshake_time

        except Exception as e:
            logging.error(f"Error checking peer handshake: {str(e)}")
            return False, ""
        finally:
            if self._client_pool:
                self._client_pool.disconnect()
                self._client_pool = None

    async def get_peer_usage_data(self, interface_name: str, peer_comment: str) -> dict:
        """
        Get usage data for a peer.

        Args:
            interface_name: Name of the WireGuard interface
            peer_comment: Comment/identifier of the peer

        Returns:
            Dict with usage data including:
            - last_handshake: datetime or None
            - download_bytes: int
            - upload_bytes: int
            - total_bytes: int
        """
        try:
            # Ensure connection to router
            await self._ensure_connected()
            api = self._client_pool.get_api()

            # Find the peer by comment
            peer = await self._find_peer_by_comment(api, interface_name, peer_comment)

            if not peer:
                logging.error(f"Peer not found: {peer_comment}")
                return {}

            # Extract usage data
            result = {}

            # Handle handshake timestamp
            if "last-handshake" in peer and peer["last-handshake"] not in [
                "0",
                "never",
                "",
            ]:
                result["last_handshake"] = peer["last-handshake"]

            else:
                result["last_handshake"] = None

            # Handle data transfer - make sure to handle potential non-numeric values
            try:
                if "rx" in peer:
                    # Remove any non-numeric characters (like 'KiB', 'MiB', etc.)
                    rx_value = "".join(c for c in peer["rx"] if c.isdigit())
                    result["download_bytes"] = int(rx_value) if rx_value else 0
                else:
                    result["download_bytes"] = 0

                if "tx" in peer:
                    # Remove any non-numeric characters
                    tx_value = "".join(c for c in peer["tx"] if c.isdigit())
                    result["upload_bytes"] = int(tx_value) if tx_value else 0
                else:
                    result["upload_bytes"] = 0
            except Exception as e:
                logging.warning(f"Error parsing traffic data: {e}")
                result["download_bytes"] = 0
                result["upload_bytes"] = 0

            # Calculate total
            result["total_bytes"] = result["download_bytes"] + result["upload_bytes"]

            return result

        except Exception as e:
            logging.error(f"Error getting peer usage data: {str(e)}")
            return {}
        finally:
            if self._client_pool:
                self._client_pool.disconnect()
                self._client_pool = None

    async def delete_peer(self, interface_name: str, peer_comment: str) -> bool:
        """
        Delete a WireGuard peer from the router.

        Args:
            interface_name: Name of the WireGuard interface
            peer_comment: Comment/identifier of the peer to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure connection to router
            await self._ensure_connected()
            api = self._client_pool.get_api()

            # Find the peer by comment
            peer = await self._find_peer_by_comment(api, interface_name, peer_comment)

            if not peer:
                logging.error(f"Peer not found: {peer_comment}")
                return False

            # Delete the peer
            success = await self._delete_peer(api, interface_name, peer["id"])

            if success:
                logging.info(f"Successfully deleted peer: {peer_comment}")
                return True
            else:
                logging.error(f"Failed to delete peer: {peer_comment}")
                return False

        except Exception as e:
            logging.error(f"Error deleting peer {peer_comment}: {str(e)}")
            return False
        finally:
            if self._client_pool:
                self._client_pool.disconnect()
                self._client_pool = None
