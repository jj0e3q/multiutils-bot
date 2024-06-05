import asyncio
import aiohttp
import json

from aiogram import Router, F
from aiogram.utils.markdown import hcode
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards.builders import inline_builder
from utils.states import TakeCity

from motor.core import AgnosticDatabase as MDB

router = Router()


async def fetch_LonLat(session, url):
    async with session.get(url) as response:
        data = await response.json()
        lat = data[0]['lat']
        lon = data[0]['lon']
        return lat, lon

async def fetch_weather(session, lat, lon, api_token):
    url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&lang=ru&units=metric&appid={api_token}'
    async with session.get(url) as response:
        data = await response.json()
        return data

@router.callback_query(F.data == "weather")
async def weathercp(query: CallbackQuery, state: FSMContext, db: MDB, weather_api_token: str) -> None:
    user = await db.users.find_one({"_id": query.from_user.id})

    if user['city'] is None:
        await state.set_state(TakeCity.city)
        await query.message.reply("Пожалуйста напишите свой город на латинице!")
    else:
        city = user['city']
        url = f'http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={weather_api_token}'
        async with aiohttp.ClientSession() as session:
            lat, lon = await fetch_LonLat(session, url)
            weather_data = await fetch_weather(session, lat, lon, weather_api_token)
            
            weather_description = weather_data['weather'][0]['description']
            temp = weather_data['main']['temp']
            feels_like = weather_data['main']['feels_like']

            await query.message.edit_text(
                f"Погода в {weather_data['name']} на сегодня:\n\n"
                f"{hcode(f'Будет {weather_description}\nТемпература: {temp}°\nОщущается как: {feels_like}°')}",
                reply_markup=inline_builder(
                    ["Поменять город", "← Назад"],
                    ["change_city", "main_page"],
                    1
                )
            )

@router.message(TakeCity.city)
async def weathercp(message: Message, state: FSMContext, db: MDB, weather_api_token: str):
    city = message.text.strip()

    await db.users.update_one({"_id": message.from_user.id}, {"$set": {'city': city}})

    await state.clear()

    url = f'http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={weather_api_token}'
    async with aiohttp.ClientSession() as session:
        lat, lon = await fetch_LonLat(session, url)
        weather_data = await fetch_weather(session, lat, lon, weather_api_token)
        
        weather_description = weather_data['weather'][0]['description']
        temp = weather_data['main']['temp']
        feels_like = weather_data['main']['feels_like']

        await message.reply(
            f"Погода в {weather_data['name']} на сегодня:\n\n"
            f"{hcode(f'Будет {weather_description}\nТемпература: {temp}°\nОщущается как: {feels_like}°')}",
            reply_markup=inline_builder(
                ["Поменять город", "← Назад"],
                ["change_city", "main_page"],
                1
            )
        )

@router.callback_query(F.data == 'change_city')
async def change_city(query: CallbackQuery, state: FSMContext, db: MDB) -> None:
    await state.set_state(TakeCity.city)
    await query.message.reply("Пожалуйста напишите город на латинице!\nПример: Almaty")