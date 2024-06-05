import sys
import asyncio
import logging
import configparser

from contextlib import suppress

from aiogram import Router, Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticDatabase as MDB

from keyboards.builders import inline_builder
from callbacks import weather

from pymongo.errors import DuplicateKeyError


router = Router()


@router.message(CommandStart())
@router.callback_query(F.data == 'main_page')
async def start(message: Message | CallbackQuery, db: MDB) -> None:
    user_c = {
        "_id": message.from_user.id,
        "full_name": message.from_user.full_name,
        "username": message.from_user.username,
        "is_premium": message.from_user.is_premium,
        "city": None
    }

    with suppress(DuplicateKeyError):
        await db.users.insert_one(user_c)

    user = await db.users.find_one({"_id": message.from_user.id})

    pattern = dict(
        text=f"Здравствуй, {user['full_name']}\n\nЯ твой бот помощник!",
        reply_markup=inline_builder(
            'Погода🍃', 'weather', 1
        )
    )
    
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(**pattern)
        await message.answer()
    else:
        await message.answer(**pattern)


async def main() -> None:

    config = configparser.ConfigParser()
    config.read('config.ini')

    token = config.get('BOT', 'token')
    weather_api_token = config.get('BOT', 'weatherToken')

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_routers(
        router,
        weather.router
    )

    cluster = AsyncIOMotorClient(host="localhost", port=27017)
    db = cluster.MultiBot

    await bot.delete_webhook(True)
    await dp.start_polling(bot, db=db, weather_api_token=weather_api_token)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    try:
        asyncio.run(main())
    except Exception as e:
        raise e