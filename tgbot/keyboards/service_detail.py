from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.database.models import ServiceStatus, Service
from tgbot.handlers.service_details import SERVICE_ACTION_PREFIX
from tgbot.services.back_button import add_return_buttons


def create_service_details_keyboard(service: Service) -> InlineKeyboardMarkup:
    """Create keyboard for service details with all available actions."""
    builder = InlineKeyboardBuilder()

    # First row: Status toggle and Reset key
    if service.status == ServiceStatus.ACTIVE:
        builder.button(
            text="❌ غیرفعال کردن",
            callback_data=f"{SERVICE_ACTION_PREFIX['DISABLE']}{service.id}",
        )
    else:
        builder.button(
            text="✅ فعال کردن",
            callback_data=f"{SERVICE_ACTION_PREFIX['ENABLE']}{service.id}",
        )
    builder.button(
        text="🔄 تعویض کلید",
        callback_data=f"{SERVICE_ACTION_PREFIX['RESET_KEY']}{service.id}",
    )

    # Second row: Renew and Config
    builder.button(
        text="📅 تمدید",
        callback_data=f"{SERVICE_ACTION_PREFIX['RENEW']}{service.id}",
    )
    builder.button(
        text="📁 کانفیگ‌ها",
        callback_data=f"{SERVICE_ACTION_PREFIX['CONFIG']}{service.id}",
    )

    # Third row: Set name
    builder.button(
        text="✏️ تنظیم نام دلخواه",
        callback_data=f"{SERVICE_ACTION_PREFIX['SET_NAME']}{service.id}",
    )

    # Adjust keyboard layout: 2 buttons per row except last row
    builder.adjust(2, 2, 1)

    # Add return buttons
    add_return_buttons(builder, "services", include_main_menu=True)

    return builder.as_markup()
