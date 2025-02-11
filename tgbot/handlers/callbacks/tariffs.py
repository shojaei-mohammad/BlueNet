import logging

from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import NoResultFound

from infrastructure.database.models import ServiceType
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.back_button import add_return_buttons


async def handle_dynamic_tariffs(callback: CallbackQuery, repo: RequestsRepo):
    """Handle the 'dynamic' callback."""
    try:
        tariffs = await repo.tariffs.get_tariffs_by_service_type(
            service_type=ServiceType.DYNAMIC
        )

        kb = InlineKeyboardBuilder()
        for tariff in tariffs:
            button_text = f"{tariff.description}"
            kb.button(text=button_text, callback_data=f"purchase_{tariff.id}")

        kb.adjust(1)
        markup = add_return_buttons(
            kb_builder=kb, back_callback="create_service", include_main_menu=True
        )

        await callback.message.edit_text(
            text="جهت خرید یکی از تعرفه های زیر را انتخاب کنید.👇",
            reply_markup=markup,
        )
    except NoResultFound:
        await callback.message.edit_text(
            text="در حال حاضر هیچ تعرفه‌ای موجود نیست.",
            reply_markup=add_return_buttons(
                kb_builder=InlineKeyboardBuilder(),
                back_callback="create_service",
                include_main_menu=True,
            ),
        )
    except Exception as e:
        logging.error(f"Error displaying tariffs: {e}", exc_info=True)
        await callback.message.edit_text(
            text="متأسفانه مشکلی در نمایش تعرفه‌ها پیش آمده است. لطفاً بعداً تلاش کنید.",
            reply_markup=add_return_buttons(
                kb_builder=InlineKeyboardBuilder(),
                back_callback="create_service",
                include_main_menu=True,
            ),
        )


async def handle_fixed_tariffs(callback: CallbackQuery, repo: RequestsRepo):
    """Handle the 'fixed' callback."""
    try:
        countries = await repo.countries.get_all_countries()

        kb = InlineKeyboardBuilder()
        for country in countries:
            kb.button(
                text=f"{country.name}", callback_data=f"fixed_country_{country.code}"
            )
        kb.adjust(2)
        markup = add_return_buttons(
            kb_builder=kb, back_callback="manage_services", include_main_menu=True
        )

        await callback.message.edit_text(
            text="لطفاً کشور مورد نظر خود را انتخاب کنید:",
            reply_markup=markup,
        )
    except NoResultFound:
        await callback.message.edit_text(
            text="در حال حاضر هیچ کشوری موجود نیست.",
            reply_markup=add_return_buttons(
                kb_builder=InlineKeyboardBuilder(),
                back_callback="create_service",
                include_main_menu=True,
            ),
        )
    except Exception as e:
        logging.error(f"Error displaying countries: {e}", exc_info=True)
        await callback.message.edit_text(
            text="متأسفانه مشکلی در نمایش کشورها پیش آمده است. لطفاً بعداً تلاش کنید.",
            reply_markup=add_return_buttons(
                kb_builder=InlineKeyboardBuilder(),
                back_callback="manage_services",
                include_main_menu=True,
            ),
        )


async def handle_fixed_country(callback: CallbackQuery, repo: RequestsRepo):
    pass
