# tgbot/states/admin.py
from aiogram.fsm.state import State, StatesGroup


class SellerRegistration(StatesGroup):
    SET_DISCOUNT = State()
    SET_DEBT_LIMIT = State()
    CONFIRM_DETAILS = State()


class InputCustomMessage(StatesGroup):
    wait_for_message = State()
