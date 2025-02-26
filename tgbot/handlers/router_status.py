# Create in tgbot/handlers/router_status.py

import logging
from typing import Dict, List, Optional

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.repo.requests import RequestsRepo
from infrastructure.services.wireguard import WireguardManager
from tgbot.models.wireguard import WireguardConfig
from tgbot.services.back_button import add_return_buttons

# Create a router for handling router status queries
router_status_router = Router()

# Define callback prefix
ROUTER_STATUS_PREFIX = "routers"


def create_router_status_keyboard(
    routers_with_status: List[Dict],
    routers_with_interfaces: Dict[str, List[str]],
    router_order: Optional[List[str]] = None,
):
    """
    Create a keyboard with router status buttons.

    Args:
        routers_with_status: List of dictionaries containing router and status info
        routers_with_interfaces: Dictionary mapping router IDs to interface names
        router_order: Optional list of router IDs in the desired order

    Returns:
        InlineKeyboardMarkup: Keyboard with router status buttons
    """
    builder = InlineKeyboardBuilder()

    # If a custom order is provided, use it
    if router_order:
        # Create a mapping of router IDs to their data for easy lookup
        router_map = {str(r["router"].id): r for r in routers_with_status}

        # Add buttons in the specified order
        for router_id in router_order:
            if router_id in router_map:
                router_data = router_map[router_id]
                add_router_button(builder, router_data, routers_with_interfaces)

        # Add any remaining routers that weren't in the order list
        for router_data in routers_with_status:
            if str(router_data["router"].id) not in router_order:
                add_router_button(builder, router_data, routers_with_interfaces)
    else:
        # No custom order, just add all routers
        for router_data in routers_with_status:
            add_router_button(builder, router_data, routers_with_interfaces)

    # Adjust keyboard layout - one button per row
    builder.adjust(1)

    # Add return button
    add_return_buttons(builder, "users_main_menu")

    return builder.as_markup()


def add_router_button(
    builder: InlineKeyboardBuilder,
    router_data: Dict,
    routers_with_interfaces: Dict[str, List[str]],
):
    """
    Add a router button to the keyboard builder.

    Args:
        builder: InlineKeyboardBuilder to add button to
        router_data: Dictionary containing router and status info
        routers_with_interfaces: Dictionary mapping router IDs to interface names
    """
    router = router_data["router"]
    is_active = router_data["is_active"]

    # Get status emoji
    status_emoji = "🟢" if is_active else "🔴"

    # Get interface names for this router
    router_id_str = str(router.id)
    interface_names = routers_with_interfaces.get(router_id_str, [])

    # Format interfaces as (interface1, interface2, ...)
    interfaces_text = ""
    if interface_names:
        interfaces_text = f" ({', '.join(interface_names)})"

    # Create button text with status emoji, hostname, and interfaces
    button_text = f"{status_emoji} {router.hostname}{interfaces_text}"

    # Add button to builder - using router_status as callback
    builder.button(text=button_text, callback_data=ROUTER_STATUS_PREFIX)


@router_status_router.callback_query(F.data == ROUTER_STATUS_PREFIX)
async def show_router_status(callback: CallbackQuery, repo: RequestsRepo):
    """
    Show status of all routers as buttons.
    """
    try:
        # Answer callback to prevent "loading" icon
        await callback.answer()

        # Show a temporary "loading" message
        await callback.message.edit_text("⏳ در حال بررسی وضعیت سرورها...")

        # Get all routers from database using the existing repo method
        routers = await repo.routers.get_all_routers()

        if not routers:
            await callback.message.edit_text("❌ هیچ سروری یافت نشد.")
            return

        # Check status for each router and collect interface data
        routers_with_status = []
        routers_with_interfaces = {}

        for router in routers:
            # Create WireguardConfig for the router
            wg_config = WireguardConfig(
                router_host=router.hostname,
                router_port=router.api_port,
                router_user=router.username,
                router_password=router.password,
                endpoint="",  # Not needed for connection test
                public_key="",  # Not needed for connection test
                subnet="",  # Not needed for connection test
                dns_servers="",  # Not needed for connection test
                allowed_ips="",  # Not needed for connection test
            )

            # Initialize WireGuard manager and test connection
            wg_manager = WireguardManager(wg_config)
            is_active = await wg_manager.test_connection()

            # If status changed, update in database
            if router.is_active != is_active:
                await repo.routers.update_router_status(router.id, is_active)
                router.is_active = is_active  # Update local object too

            # Add to results
            routers_with_status.append({"router": router, "is_active": is_active})

            # Get interfaces for this router using the repository method
            interfaces = await repo.routers.get_interfaces_by_router_id(router.id)
            interface_names = [interface.interface_name for interface in interfaces]
            routers_with_interfaces[str(router.id)] = interface_names

        # You can define a custom order here if needed
        # Example: router_order = ["uuid1", "uuid2", "uuid3"]
        router_order = None

        # Create keyboard with router status buttons
        keyboard = create_router_status_keyboard(
            routers_with_status, routers_with_interfaces, router_order
        )

        # Update message with router status keyboard
        await callback.message.edit_text(
            "🖥 وضعیت سرورها:\n\n"
            "🟢 = فعال | 🔴 = غیرفعال\n\n"
            "لیست سرورها و وضعیت آنها:",
            reply_markup=keyboard,
        )

    except Exception as e:
        logging.error(f"Error in show_router_status: {e}", exc_info=True)
        await callback.message.edit_text("❌ خطا در بررسی وضعیت سرورها.")
