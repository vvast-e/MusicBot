

import asyncio
import logging
from aiogram import Bot, Dispatcher, types,F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import config
import lyricsgenius
import requests
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO)
# Объект бота и API genius
bot = Bot(token=config.bot_token.get_secret_value())
genius_API =config.genius_api.get_secret_value()
# Диспетчер
dp = Dispatcher()
genius=lyricsgenius.Genius(genius_API)

GENIUS_API_URL = "https://api.genius.com"
HEADERS = {
    "Authorization": f"Bearer {genius_API}"
}

class Form(StatesGroup):
    waiting_for_song_lyrics = State()  # Ожидание строки песни
    waiting_for_artist_name = State()  # Ожидание имени исполнителя
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    reply_kb=[
        [types.KeyboardButton(text="Строчка песни")],
        [types.KeyboardButton(text="Топ-10 чарта")],
        [types.KeyboardButton(text="Исполнитель")],
    ]
    keyboard=types.ReplyKeyboardMarkup(
        keyboard=reply_kb,
        resize_keyboard=True,
    )
    await message.answer("Привет! Отправь мне строчку из песни, исполнителя, и я постараюсь найти все, что тебя интересует на Genius.com.",
                         reply_markup=keyboard)




@dp.message(lambda message: message.text == "Строчка песни")
async def handle_search_song(message: types.Message, state: FSMContext):
    await message.answer("Хорошо, жду строчку.")
    await state.set_state(Form.waiting_for_song_lyrics)

@dp.message(Form.waiting_for_song_lyrics)
async def search_song(message: types.Message, state: FSMContext):
    user_input = message.text
    try:
        song = genius.search_song(user_input)
        if song:
            response_text = f"Найдена песня: {song.title} — {song.artist}\nСсылка: {song.url}"
        else:
            response_text = "Песня не найдена по этой строчке."
        await message.reply(response_text)
    except Exception as e:
        await message.reply(f"Произошла ошибка: {str(e)}")
    await state.clear()
def get_artist_songs(artist_name):
    url = 'https://api.genius.com/search'
    headers = {'Authorization': f'Bearer {genius_API}'}
    params = {'q': artist_name}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        hits = data['response']['hits']


        artist_id = None
        for hit in hits:
            if hit['result']['primary_artist']['name'].lower() == artist_name.lower():
                artist_id = hit['result']['primary_artist']['id']
                break

        if artist_id:

            return get_top_songs_by_artist(artist_id)
        else:
            return None, "Исполнитель не найден."
    else:
        return None, "Ошибка при запросе данных."



def get_top_songs_by_artist(artist_id):
    url = f'https://api.genius.com/artists/{artist_id}/songs'
    headers = {'Authorization': f'Bearer {genius_API}'}
    params = {'sort': 'popularity', 'per_page': 5, 'page': 1}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        songs = data['response']['songs']

        if songs:
            top_songs = [f"{song['title']} - {song['url']}" for song in songs[:5]]
            return top_songs, None
        else:
            return None, "Песни не найдены."
    else:
        return None, f"Ошибка при запросе данных: {response.status_code}"




@dp.message(lambda message: message.text == "Исполнитель")
async def handle_artist_name(message: types.Message, state: FSMContext):
    await message.answer("Жду Имя исполнителя.")
    await state.set_state(Form.waiting_for_artist_name)

@dp.message(Form.waiting_for_artist_name)
async def handle_artist_out(message: types.Message, state: FSMContext):
    artist_name = message.text
    await message.answer(f"Ищу топ 5 песен для исполнителя: {artist_name}")
    top_songs, error = get_artist_songs(artist_name)

    if top_songs:
        await message.answer("\n".join(top_songs))
    else:
        await message.answer(error)
    await state.clear()


def search_songbyname(song_name):
    song = genius.search_song(song_name)
    if song:
        response_text = f" {song.title} — {song.artist}\n"

    else:
        response_text = "Песня не найдена по этой строчке."
    return response_text




def get_top_10_songs_from_chart():
    url = 'https://genius.com/#top-songs'

    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        chart = soup.find('div', {'id': 'application'})
        if chart:

            top_songs = []
            songs = chart.find_all('h3', limit=10)
            for i, song in enumerate(songs):
                title = song.get_text(strip=True)[:-6]

                top_songs.append(f"{i + 1}. {search_songbyname(title)}")

            return top_songs, None
        else:
            return None, "Чарт не найден на странице."
    else:
        return None, f"Ошибка при запросе страницы: {response.status_code}"


@dp.message(lambda message: message.text == "Топ-10 чарта")
async def get_top_chart(message: types.Message):
    await message.answer("Ищу топ-10 песен...")

    top_songs, error = get_top_10_songs_from_chart()

    if top_songs:
        await message.answer("\n".join(top_songs))
    else:
        await message.answer(error)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
        asyncio.run(main())

