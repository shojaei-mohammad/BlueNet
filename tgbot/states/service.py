# Define states for custom name setting
from aiogram.fsm.state import StatesGroup, State


class ServiceStates(StatesGroup):
    waiting_for_name = State()
