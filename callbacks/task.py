import uuid
import datetime
import asyncio

from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.markdown import hcode
from aiogram.fsm.context import FSMContext

from keyboards.builders import inline_builder
from utils.states import Task

from motor.core import AgnosticDatabase as MDB

router = Router()

time_options = [
    ("Через 30 минут", 30),
    ("Через 1 час", 60),
    ("Через 2 часа", 120),
    ("Завтра в это же время", 1440)
]

@router.callback_query(F.data == 'task')
async def task_create(query: CallbackQuery, db: MDB, state: FSMContext) -> None:
    await state.set_state(Task.task_name)
    await query.message.answer("Пожалуйста, введите название задачи")

@router.message(Task.task_name)
async def task_name_c(message: Message, db: MDB, state: FSMContext) -> None:
    await state.update_data(task_name=message.text)
    await state.set_state(Task.time_task)

    keyboard = inline_builder(
        [text for text, _ in time_options] + ["Ввести вручную"],
        [f'time_{minutes}' for _, minutes in time_options] + ["manual_time"],
        sizes=1
    )
    await message.answer("Когда задача будет выполнена? Выберите один из вариантов или введите вручную:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("time_") | F.data == "manual_time")
async def time_task_c(query: CallbackQuery, db: MDB, state: FSMContext, bot: Bot) -> None:
    if query.data == "manual_time":
        await state.set_state(Task.manual_time_task)
        await query.message.answer("Пожалуйста, введите время в формате 'ДД.ММ.ГГГГ ЧЧ:ММ'.")
        return

    minutes = int(query.data.split("_")[1])
    task_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    
    data = await state.get_data()
    task = create_task_dict(data, query.message, task_time)
    
    await db.tasks.insert_one(task)
    await query.message.answer(f"Напоминание <b>{hcode(data['task_name'])}</b> было успешно создано!\n\nУведомление придет в {hcode(task_time.strftime('%d.%м.%Y %H:%М'))}")
    
    asyncio.create_task(schedule_task_notification(task, query.message.chat.id, bot, db))

@router.message(Task.manual_time_task)
async def manual_time_task_c(message: Message, db: MDB, state: FSMContext, bot: Bot) -> None:
    try:
        print(f"User entered time: {message.text}")  # Отладочное сообщение для ввода времени
        task_time = datetime.datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")  # Используем .strip() чтобы убрать лишние пробелы
        
        data = await state.get_data()
        task = create_task_dict(data, message, task_time)

        await db.tasks.insert_one(task)
        await message.answer(f"Напоминание <b>{hcode(data['task_name'])}</b> было успешно создано!\n\nУведомление придет в {hcode(task_time.strftime('%d.%m.%Y %H:%M'))}")
        
        asyncio.create_task(schedule_task_notification(task, message.chat.id, bot, db))


    except ValueError as e:
        await message.answer("Неверный формат времени. Пожалуйста, введите время в формате 'ДД.ММ.ГГГГ ЧЧ:ММ'.")
        print(f"Incorrect time format entered: {message.text} - Error: {e}")

def create_task_dict(data: dict, message: Message, task_time: datetime.datetime) -> dict:
    return {
        "_id": str(uuid.uuid4()),
        "username_c": message.from_user.username,
        "user_id": message.from_user.id,
        "NameTask": data['task_name'],
        "TimeTask": task_time,
        "CreateTime": datetime.datetime.now()
    }

async def schedule_task_notification(task: dict, chat_id: int, bot: Bot, db: MDB) -> None:
    task_time = task['TimeTask']
    now = datetime.datetime.now()
    delay = (task_time - now).total_seconds()

    if delay > 0:
        await asyncio.sleep(delay)
    
    await bot.send_message(chat_id, f"Напоминание <b>{hcode(task['NameTask'])}</b>!\n\nВремя для задачи наступило!")
    
    await db.tasks.delete_one({"_id": task["_id"]})
