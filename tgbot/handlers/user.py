import logging

from aiogram import Router
from aiogram.filters import CommandStart, CommandObject, or_f
from aiogram.types import Message
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.payload import decode_payload

from infrastructure.database.models import BotUser
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.keyboards.menu import create_markup

user_router = Router()


@user_router.message(or_f(CommandStart(deep_link=True), CommandStart()))
async def user_start(
    message: Message,
    command: CommandObject,
    repo: RequestsRepo,
    user: BotUser,
):
    chat_id = message.chat.id
    args = command.args
    try:
        markup, text = await create_markup("users_main_menu")
        referral_link = await create_start_link(message.bot, str(chat_id), encode=True)

        # Decode referrer ID from command args if present
        referrer_chat_id = decode_payload(args) if args else None
        await repo.users.get_or_create_user(
            chat_id=chat_id,
            name=message.chat.first_name,
            last_name=message.chat.last_name,
            username=message.chat.username,
            referral_code=chat_id,
            referral_link=referral_link,
        )

        if referrer_chat_id and not user.ReferredBy:
            # If the user has a referrer, and it's not already set
            await repo.users.update_referred_by(chat_id, int(referrer_chat_id))
            await repo.users.update_referral_count(int(referrer_chat_id))
            logging.info(
                f"Referrer {referrer_chat_id} updated for new user Chat-id {chat_id}."
            )

        # Welcome message or updated information if the user is revisiting
        await message.answer(text=text, reply_markup=markup)
    except UnicodeDecodeError:
        logging.error("Codec can't decode command args - Invalid start byte")
    except Exception as e:
        logging.error(f"An unknown error occurred.\n Error: {e}")
