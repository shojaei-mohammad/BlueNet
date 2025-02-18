from aiogram.fsm.state import StatesGroup, State


class SearchStates(StatesGroup):
    """States for service search process."""

    WAITING_FOR_PUBLIC_ID = State()
    WAITING_FOR_IP = State()
