from typing import Optional

from pydantic import BaseModel, Field


class PurchaseData(BaseModel):
    user_id: str = Field(
        ..., description="Unique ID of the user purchasing the service."
    )
    email: str = Field(..., description="Email of the user.")
    duration_days: int = Field(..., description="Duration of the service in days.")
    interface_name: str = Field(
        default="wireguard1", description="Name of the WireGuard interface."
    )
    comment: Optional[str] = Field(
        default=None, description="Optional comment for the peer."
    )
    seller_id: int = Field(..., description="ID of the seller.")
    purchase_id: UUID = Field(..., description="Unique ID of the purchase.")


class WireguardConfig(BaseModel):
    router_host: str = Field(..., description="Hostname or IP of the MikroTik router.")
    router_user: str = Field(..., description="Username for the MikroTik router.")
    router_password: str = Field(..., description="Password for the MikroTik router.")
    router_port: int = Field(default=8728, description="Port for the MikroTik API.")
    subnet: str = Field(default="10.10.0.0/24", description="Subnet for IP allocation.")
    dns_servers: str = Field(
        default="1.1.1.1", description="DNS servers for the client."
    )
    allowed_ips: str = Field(
        default="0.0.0.0/0", description="Allowed IPs for the client."
    )
    endpoint: str = Field(
        default="vpn.example.com:13231", description="Endpoint for the client."
    )


class WireguardPeerConfig(BaseModel):
    interface_name: str = Field(..., description="Name of the WireGuard interface.")
    private_key: str = Field(..., description="Private key for the peer.")
    public_key: str = Field(..., description="Public key for the peer.")
    allowed_ip: str = Field(..., description="IP address allocated to the peer.")
    comment: str = Field(..., description="Unique comment for the peer.")
