import logging

from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import NoResultFound

from infrastructure.database.models import ServiceType, Seller
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.back_button import add_return_buttons
from tgbot.services.utils import format_currency, convert_english_digits_to_farsi


async def handle_tariffs(
    callback: CallbackQuery,
    seller: Seller,
    repo: RequestsRepo,
    service_type: ServiceType = None,
    country_code: str = None,
):
    try:
        if service_type:
            tariffs = await repo.tariffs.get_tariffs_by_service_type(
                service_type=service_type
            )
        elif country_code:
            tariffs = await repo.tariffs.get_tariffs_by_country_code(
                country_code=country_code
            )
        else:
            raise ValueError("Either service_type or country_code must be provided")

        text = "📋 لیست تعرفه‌های موجود:\n\n"
        kb = InlineKeyboardBuilder()

        # For dynamic IPs, create a separate section for each tariff
        for tariff in tariffs:
            # Calculate seller price and profit
            original_price = tariff.price
            seller_price = original_price * (1 - seller.discount_percent / 100)
            profit = original_price - seller_price

            # Add tariff details to the message
            text += (
                f"📍 {tariff.description}\n"
                f"💰 قیمت اصلی: {format_currency(original_price, convert_to_farsi=True)} تومان\n"
                f"💵 قیمت فروش: {format_currency(seller_price, convert_to_farsi=True)} تومان\n"
                f"📈 سود شما: {format_currency(profit, convert_to_farsi=True)} تومان\n"
                f"⏱ مدت: {convert_english_digits_to_farsi(tariff.duration_days)} روز\n\n"
            )

            if service_type == ServiceType.DYNAMIC:
                # Add buttons for this specific tariff
                kb.button(
                    text=f"خرید {tariff.description}",
                    callback_data=f"select_quantity_{tariff.id}",
                )
            else:
                # For fixed IPs, add single purchase button
                kb.button(
                    text=f"خرید {tariff.description}",
                    callback_data=f"purchase_{tariff.id}",
                )

        kb.adjust(1)  # One button per row for better readability

        markup = add_return_buttons(
            kb_builder=kb, back_callback="create_service", include_main_menu=True
        )

        await callback.message.edit_text(
            text=text,
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


async def handle_dynamic_tariffs(
    callback: CallbackQuery, repo: RequestsRepo, seller: Seller
):
    """Handle the 'dynamic' callback."""
    await handle_tariffs(callback, seller, repo, service_type=ServiceType.DYNAMIC)


async def handle_fixed_country(
    callback: CallbackQuery, repo: RequestsRepo, seller: Seller
):
    """Handle the 'fixed' callback for specific country."""
    country_code = callback.data.split("_")[2]
    await handle_tariffs(callback, seller, repo, country_code=country_code)


async def handle_fixed_tariffs(callback: CallbackQuery, repo: RequestsRepo):
    """Handle the 'fixed' callback for country selection."""
    try:
        countries = await repo.countries.get_all_countries()

        text = "🌍 لطفاً کشور مورد نظر خود را انتخاب کنید:\n\n"
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
            text=text,
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


# async def handle_tariff_detail(
#     callback: CallbackQuery,
#     repo: RequestsRepo,
#     seller: Seller,
#     tariff_id: UUID,
#     wireguard_manager: WireguardManager,
# ):
#     """Handle displaying tariff details and purchase options."""
#     try:
#         tariff_details = await repo.tariffs.get_tariff_details(tariff_id)
#         if not tariff_details:
#             await callback.answer("تعرفه مورد نظر یافت نشد.", show_alert=True)
#             return
#
#         text = (
#             f"📋 جزئیات تعرفه\n\n"
#             f"📍 {tariff_details.description}\n"
#             f"💰 قیمت: {format_currency(tariff_details.price)} تومان\n"
#             f"⏱ مدت: {tariff_details.duration_days} روز\n"
#         )
#
#         kb = InlineKeyboardBuilder()
#
#         if tariff_details.service_type == ServiceType.DYNAMIC:
#             # Add bulk purchase options for dynamic IPs
#             kb.button(text="1️⃣", callback_data=f"purchase_{tariff_id}_1")
#             kb.button(text="3️⃣", callback_data=f"purchase_{tariff_id}_3")
#             kb.button(text="5️⃣", callback_data=f"purchase_{tariff_id}_5")
#             kb.button(text="🔟", callback_data=f"purchase_{tariff_id}_10")
#             kb.button(text="تعداد دلخواه", callback_data=f"custom_quantity_{tariff_id}")
#             kb.adjust(2)
#         else:
#             # Single purchase option for fixed IPs
#             kb.button(text="خرید", callback_data=f"purchase_{tariff_id}")
#             kb.adjust(1)
#
#         markup = add_return_buttons(
#             kb_builder=kb,
#             back_callback=(
#                 "dynamic"
#                 if tariff_details.service_type == ServiceType.DYNAMIC
#                 else "fixed"
#             ),
#             include_main_menu=True,
#         )
#
#         await callback.message.edit_text(text=text, reply_markup=markup)
#
#     except Exception as e:
#         logging.error(f"Error displaying tariff details: {e}", exc_info=True)
#         await callback.answer(
#             "متأسفانه مشکلی در نمایش جزئیات تعرفه پیش آمده است.", show_alert=True
#         )
