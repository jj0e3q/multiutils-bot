import sys
import asyncio
import logging
import configparser

from contextlib import suppress

from aiogram import Router, Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hcode
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticDatabase as MDB

from pymongo.errors import DuplicateKeyError


router = Router()


@router.message(CommandStart())
async def start(message: Message, db: MDB) -> None:
    user_c = {
        "_id": message.from_user.id,
        "full_name": message.from_user.full_name,
        "username": message.from_user.username,
        "is_premium": message.from_user.is_premium
    }

    with suppress(DuplicateKeyError):
        await db.users.insert_one(user_c)

    user = await db.users.find_one({"_id": message.from_user.id})

    await message.reply(
        f"Здравствуй, {user['full_name']}\n\n"
        "Я твой бот помощник!"
    )


async def main() -> None:

    config = configparser.ConfigParser()
    config.read('config.ini')

    token = config.get('BOT', 'token')

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_routers(
        router
    )

    cluster = AsyncIOMotorClient(host="localhost", port=27017)
    db = cluster.MultiBot

    await bot.delete_webhook(True)
    await dp.start_polling(bot, db=db)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    try:
        asyncio.run(main())
    except Exception as e:
        raise e