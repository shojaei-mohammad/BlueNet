# tgbot/states/purchase.py
from aiogram.fsm.state import State, StatesGroup


class PurchaseState(StatesGroup):
    SELECTING_QUANTITY = State()
    CONFIRMING_PURCHASE = State()
