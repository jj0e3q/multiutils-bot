import uuid
import datetime
import asyncio

from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards.builders import inline_builder
from utils.states import Task

from motor.core import AgnosticDatabase as MDB

router = Router()


@router.callback_query(F.data == 'task')
async def task_create(query: CallbackQuery, db: MDB, state: FSMContext) -> None:
    await state.set_state(Task.task_name)
    await query.message.answer("Пожалуйста, введите название задачи")

@router.message(Task.task_name)
async def task_name_c(message: Message, db: MDB, state: FSMContext) -> None:
    await state.update_data(task_name=message.text)
    await state.set_state(Task.time_task)
    await message.answer("Когда задача будет выполнена?\nПожалуйста, введите время в формате 'ДД.ММ.ГГГГ ЧЧ:ММ'.")

@router.message(Task.time_task)
async def time_task_c(message: Message, db: MDB, state: FSMContext, bot: Bot) -> None:
    try:
        task_time = datetime.datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        
        data = await state.get_data()
        
        task = {
            "_id": str(uuid.uuid4()),
            "username_c": message.from_user.username,
            "user_id": message.from_user.id,
            "NameTask": data['task_name'],
            "TimeTask": task_time,
            "CreateTime": datetime.datetime.now()
        }

        await db.tasks.insert_one(task)
        await message.answer(f"Задача {data['task_name']} на {task_time.strftime('%d.%m.%Y %H:%M')}")

        asyncio.create_task(schedule_task_notification(task, message.chat.id, bot))

    except ValueError:
        await message.answer("Неверный формат времени. Пожалуйста, введите время в формате 'ДД.ММ.ГГГГ ЧЧ:ММ'.")

async def schedule_task_notification(task, chat_id, bot):
    task_time = task['TimeTask']
    now = datetime.datetime.now()

    delay = (task_time - now).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
    
    await bot.send_message(chat_id, f"Напоминание '{task['NameTask']}': Время для задачи наступило!")