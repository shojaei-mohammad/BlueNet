from aiogram.fsm.state import State, StatesGroup


class SellerManagementState(StatesGroup):
    """States for seller management operations"""

    waiting_for_discount = State()
    waiting_for_debt_limit = State()
    waiting_for_search_query = State()
