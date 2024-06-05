from aiogram.fsm.state import StatesGroup, State

class TakeCity(StatesGroup):
    city = State()