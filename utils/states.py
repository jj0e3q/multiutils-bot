from aiogram.fsm.state import StatesGroup, State

class TakeCity(StatesGroup):
    city = State()

class Task(StatesGroup):
    task_name = State()
    time_task = State()