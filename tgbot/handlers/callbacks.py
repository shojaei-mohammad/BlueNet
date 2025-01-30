from aiogram import Router
from aiogram.types import CallbackQuery

from infrastructure.database.models import BotUser
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.keyboards.menu import menu_structure, create_markup

callback_router = Router()


@callback_router.callback_query()
async def default_callback_query(
    call: CallbackQuery,
    repo: RequestsRepo,
    user: BotUser,
):
    """
    Asynchronous handler for callback queries triggered by inline keyboard buttons.

    This function manages the user's navigation in the bot based on the callback data received
    from the inline keyboard buttons. Depending on the callback_data, this function can
    update the current message to reflect a different menu or provide feedback to the user.

    Args:
        call (CallbackQuery): The callback query object containing data about the callback.
        repo (RequestsRepo):
        user (BotUser):
    """
    # Extract relevant data from the callback query
    callback_data = call.data
    chat_id = call.message.chat.id
    # Check if the received callback_data matches any menu defined in menu_structure
    if callback_data in menu_structure:
        # Generate the appropriate markup and text for the menu corresponding to callback_data
        markup, menu_text = await create_markup(callback_data)
        await call.message.edit_text(text=menu_text, reply_markup=markup)

    else:
        await call.answer(text="منو تعریف نشده است.")
