"""Import all routers and add them to routers_list."""

from .admin import admin_router
from .callbacks import callback_router
from .echo import echo_router
from .expiring_services import expiring_services_router
from .purchase_states import purchase_router
from .router_status import router_status_router
from .service_details import service_details_router
from .service_search import search_router
from .services import services_router
from .settlement import settlement_router
from .transactions import transaction_history_router
from .user import user_router

routers_list = [
    admin_router,
    user_router,
    search_router,
    purchase_router,
    services_router,
    service_details_router,
    settlement_router,
    router_status_router,
    transaction_history_router,
    expiring_services_router,
    callback_router,
    echo_router,  # echo_router must be last
]

__all__ = [
    "routers_list",
]
