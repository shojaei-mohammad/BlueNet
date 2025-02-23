from aiogram.fsm.state import State, StatesGroup


class SettlementState(StatesGroup):
    WAITING_FOR_RECEIPT = State()
