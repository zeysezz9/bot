import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ------------------- НАЛАШТУВАННЯ -------------------
BOT_TOKEN = "8427493074:AAFBoWfxLRWKO5a1V4ju3JABu2t4RGKRJXw"  # ← заміни на свій токен

CS2_PRO_PLAYERS = [
    "ZywOo", "donk", "m0NESY", "sh1ro", "NiKo", "s1mple", "ropz",
    "flameZ", "Spinx", "KSCERATO", "torzsi", "XANTARES", "Magisk",
    "dev1ce", "frozen", "Twistzz", "b1t", "Ax1Le", "electronic", "Boombl4",
    "YEKINDAR", "SunPayus", "jabbi", "stavn", "TeSeS", "br0", "degster",
    "jL", "w0nderful", "nertZ", "chopper", "zorte", "zont1x", "kyousuke"
]

# Стани
class GameStates(StatesGroup):
    waiting = State()
    roles_distribution = State()
    discussion = State()
    finished = State()


dp = Dispatcher(storage=MemoryStorage())
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Зберігання ігор: chat_id → дані
games = {}


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Почати Шпигуна CS2", callback_data="new_game")]
    ])
    await message.answer(
        "<b>Шпигун CS2 — Про-гравці (на одному телефоні)</b>\n\n"
        "Передавайте телефон по колу\n"
        "Кожен дивиться свою роль і одразу ховає\n"
        "Один — шпигун (не знає гравця)\n"
        "Решта знають, хто це за про-гравець\n\n"
        "Натисни нижче, щоб почати!",
        reply_markup=kb
    )


@dp.callback_query(lambda c: c.data == "new_game")
async def new_game(callback: types.CallbackQuery, state: FSMContext):
    chat_id = callback.message.chat.id

    if chat_id in games:
        await callback.message.answer("Гра вже йде. Завершити — /stop")
        await callback.answer()
        return

    games[chat_id] = {
        "player_count": 0,
        "current_pro": None,
        "spy_index": None,          # номер шпигуна (0..n-1)
        "seen_count": 0,
        "phase": "waiting"
    }

    await state.set_state(GameStates.waiting)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Скільки гравців?", callback_data="set_players")]
    ])

    msg = await callback.message.edit_text(
        "Гру створено!\n\n"
        "Скільки людей буде грати?\n"
        "(мінімум 3)",
        reply_markup=kb
    )
    games[chat_id]["main_message_id"] = msg.message_id
    await callback.answer()


@dp.callback_query(lambda c: c.data == "set_players")
async def ask_player_count(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="3", callback_data="players_3")],
        [InlineKeyboardButton(text="4", callback_data="players_4")],
        [InlineKeyboardButton(text="5", callback_data="players_5")],
        [InlineKeyboardButton(text="6", callback_data="players_6")],
        [InlineKeyboardButton(text="7", callback_data="players_7")],
        [InlineKeyboardButton(text="8", callback_data="players_8")],
        [InlineKeyboardButton(text="9", callback_data="players_9")],
        [InlineKeyboardButton(text="10", callback_data="players_10")],
    ])
    await callback.message.edit_text(
        "Обери кількість гравців:",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("players_"))
async def set_player_count(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)
    if not game:
        await callback.answer()
        return

    count = int(callback.data.split("_")[1])
    if count < 3:
        await callback.answer("Мінімум 3 гравці", show_alert=True)
        return

    game["player_count"] = count
    game["spy_index"] = random.randint(0, count - 1)
    game["current_pro"] = random.choice(CS2_PRO_PLAYERS)
    game["seen_count"] = 0
    game["phase"] = "roles_distribution"

    text = (
        f"<b>Гра почалася!</b>\n"
        f"Гравців: {count}\n"
        f"Про-гравець: прихований до кінця\n\n"
        "Передавайте телефон по колу.\n"
        "Натискайте «Показати мою роль» → дивіться → «Сховати роль»\n"
        "Після перегляду передайте наступному.\n\n"
        f"Залишилось подивитись ролей: {count}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показати мою роль", callback_data="show_role")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer(f"Встановлено {count} гравців")


@dp.callback_query(lambda c: c.data == "show_role")
async def show_role(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game["phase"] != "roles_distribution":
        await callback.answer("Фаза показу ролей завершена", show_alert=True)
        return

    current_index = game["seen_count"]

    if current_index >= game["player_count"]:
        await callback.answer("Усі ролі вже роздано", show_alert=True)
        return

    is_spy = (current_index == game["spy_index"])

    if is_spy:
        text = (
            "<b>ТИ — ШПИГУН!</b>\n\n"
            "Ти НЕ знаєш, хто цей про-гравець CS2.\n"
            "Став питання про:\n"
            "• нік • роль • зброя • команда • країна • вік • турніри\n"
            "Не пали себе! Удачі 😈"
        )
    else:
        text = (
            f"<b>ТИ — АГЕНТ</b>\n\n"
            f"Про-гравець: <b>{game['current_pro']}</b>\n\n"
            "Відповідай так, ніби всі знають цього гравця.\n"
            "Не будь занадто очевидним, але й не бреши сильно."
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я подивився → сховати", callback_data="hide_role")]
    ])

    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb
        )
    except Exception:
        await callback.answer("Помилка при показі ролі", show_alert=True)
        return

    await callback.answer("Дивись роль уважно!")


@dp.callback_query(lambda c: c.data == "hide_role")
async def hide_role(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game["phase"] != "roles_distribution":
        await callback.answer()
        return

    game["seen_count"] += 1
    remaining = game["player_count"] - game["seen_count"]

    if remaining > 0:
        text = (
            f"Роль сховано.\n\n"
            f"Передай телефон наступному гравцю.\n\n"
            f"Залишилось подивитись ролей: {remaining}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Показати мою роль", callback_data="show_role")]
        ])
    else:
        text = (
            "<b>Усі ролі переглянуто!</b>\n\n"
            "Тепер можна обговорювати (5–10 хвилин)"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Почати обговорення", callback_data="start_discuss")]
        ])
        game["phase"] = "discussion"

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer("Роль сховано")


@dp.callback_query(lambda c: c.data == "start_discuss")
async def start_discussion(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game["phase"] != "discussion":
        await callback.answer()
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Завершити гру та показати результат", callback_data="finish_game")]
    ])

    await callback.message.edit_text(
        "<b>Обговорення почалося!</b>\n\n"
        "Ставте питання, дискутуйте.\n"
        "Коли закінчите — натисніть кнопку нижче",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "finish_game")
async def finish_game(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)
    if not game:
        await callback.answer()
        return

    spy_num = game["spy_index"] + 1  # 1-based
    pro = game["current_pro"]

    text = (
        "<b>Гра завершена!</b>\n\n"
        f"Шпигун був гравець № <b>{spy_num}</b>\n"
        f"Про-гравець: <b>{pro}</b>\n\n"
        "Обговоріть, хто як думав і чому 😄\n\n"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Почати нову гру", callback_data="new_game")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)

    # Очищення гри
    if chat_id in games:
        del games[chat_id]

    await callback.answer("Результат показано")


@dp.message(Command("stop"))
async def stop_game(message: types.Message):
    chat_id = message.chat.id
    if chat_id in games:
        del games[chat_id]
        await message.answer("Гру примусово завершено.")
    else:
        await message.answer("Активної гри немає.")


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())