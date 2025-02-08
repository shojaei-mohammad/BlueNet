from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def add_return_buttons(
    kb_builder: InlineKeyboardBuilder,
    back_callback: str = None,
    include_main_menu: bool = False,
) -> InlineKeyboardMarkup:
    """
    Adds common buttons to an existing inline keyboard markup.

    This function appends a 'Back' button and optionally a 'Main Menu' button to the provided inline keyboard markup.
    These buttons facilitate navigation in the bot's interface.

    Args:
        kb_builder (InlineKeyboardMarkup): The existing inline keyboard markup to which the buttons will be added.
        back_callback (str): The callback data associated with the 'Back' button.
        include_main_menu (bool, optional): Determines whether to include the 'Main Menu' button. Default is True.

    Returns:
        InlineKeyboardMarkup: The updated inline keyboard markup.
    """

    # Add a 'Back' button with the provided callback data
    if back_callback is not None:
        back_button = InlineKeyboardButton(
            text="🔙 بازگشت", callback_data=back_callback
        )
        kb_builder.row(back_button)  # This adds the button on a new row

    # Optionally add a 'Main Menu' button
    if include_main_menu:
        main_menu_button = InlineKeyboardButton(
            text="🪐 منو اصلی", callback_data="users_main_menu"
        )
        kb_builder.row(main_menu_button)  # This adds the button on a new row

    return kb_builder.as_markup()
