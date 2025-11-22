import asyncio
import re
import time

from aiogram import Bot, Dispatcher
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    CallbackQuery,
    BotCommand,
    MessageReactionUpdated,
)

import config
from storage import BotStorage


storage = BotStorage()

group_types = {ChatType.GROUP, ChatType.SUPERGROUP}


GUIDE_CALLBACK_PREFIX = "guide:"


async def schedule_delete_message(bot: Bot, chat_id: int, message_id: int, delay: int = 300) -> None:
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass
    except Exception:
        pass


def make_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Поиск гайда"),
                KeyboardButton(text="Список гайдов"),
            ],
            [
                KeyboardButton(text="Мой ранг"),
                KeyboardButton(text="Список рангов"),
            ],
            [
                KeyboardButton(text="Помощь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие или введи команду",
    )


def format_guide_button_label(key: str, text: str) -> str:
    if text:
        header = text.strip().split("\n", 1)[0].strip()
    else:
        header = key
    if header.endswith(":"):
        header = header[:-1]
    if key.startswith("switch_") and header.lower().startswith("switch "):
        header = header[7:].lstrip("-–: ")
    if key.startswith("ryazhenka_"):
        if "(Ryazhenka" not in header:
            header = f"{header} (Ryazhenka)"
    else:
        header = re.sub(r"\s*\([^)]*\)\s*$", "", header).strip()
    if key.startswith("ryazhenka_") and "(Ryazhenka" not in header:
        header = f"{header} (Ryazhenka)"
    return header or key


def build_guides_keyboard(chat_id: int) -> InlineKeyboardMarkup | None:
    guides = storage.list_guides(chat_id)
    if not guides:
        return None
    buttons = []
    for key in sorted(guides.keys()):
        label = format_guide_button_label(key, guides[key])
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{GUIDE_CALLBACK_PREFIX}{key}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def is_help_request(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    keywords = storage.list_keywords()
    return any(keyword in lowered for keyword in keywords)


async def is_user_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


async def cmd_start(message: Message, bot: Bot) -> None:
    if message.chat.type in group_types:
        await message.reply(
            "Привет! Я Ruzhenka-helper.\n"
            "Считаю активность участников и могу выдавать гайды.\n"
            "Напиши /help, чтобы посмотреть команды.",
            reply_markup=make_main_keyboard(),
        )
    else:
        me = await bot.get_me()
        username = me.username or ""
        keyboard = None
        if username:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ Добавить в группу",
                            url=f"https://t.me/{username}?startgroup=start",
                        )
                    ]
                ]
            )
        await message.answer(
            "Привет! Я Ruzhenka-helper — бот для групп.\n"
            "Добавь меня в свой чат как админа и используй /help в чате.",
            reply_markup=keyboard,
        )
        await message.answer(
            "Выбери действие на клавиатуре ниже.",
            reply_markup=make_main_keyboard(),
        )


async def cmd_help(message: Message) -> None:
    text = (
        "Команды Ruzhenka-helper:\n"
        "/myrank – показать твой ранг и количество сообщений\n"
        "/guide <ключ> – показать гайд\n"
        "/guides – список гайдов\n\n"
        "Только админы группы:\n"
        "/addrank <сообщений> <название> – добавить ранг (порог по сообщениям)\n"
        "/ranks – список рангов и их пороги\n"
        "/resetranks – сбросить ранги по умолчанию (F–S++)\n"
        "/setguide <ключ> <текст> – создать/обновить гайд\n"
        "/delguide <ключ> – удалить гайд\n"
        "/addxp <кол-во> (в ответ на сообщение) – вручную выдать сообщения/ранг\n\n"
        "Только в личном чате с ботом:\n"
        "/keywords – показать ключевые фразы\n"
        "/addkeyword <фраза> – добавить фразу\n"
        "/delkeyword <фраза> – удалить фразу\n"
    )
    await message.reply(text)


async def cmd_myrank(message: Message) -> None:
    if message.chat.type not in group_types:
        await message.reply("Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    user_id = user.id
    user_data = storage.get_user(chat_id, user_id)
    xp = int(user_data.get("xp", 0))
    rank = storage.get_rank_for_xp(chat_id, xp)
    await message.reply(f"Твой ранг: {rank}\nСообщений: {xp}")


async def cmd_addrank(message: Message, bot: Bot) -> None:
    if message.chat.type not in group_types:
        await message.reply("Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    if not await is_user_admin(bot, chat_id, user.id):
        await message.reply("Только админ чата может настраивать ранги.")
        return
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await message.reply(
            "Использование: /addrank <сообщений_минимум> <название ранга>"
        )
        return
    try:
        xp_min = int(parts[1])
    except ValueError:
        await message.reply("Количество сообщений должно быть числом.")
        return
    name = parts[2].strip()
    if not name:
        await message.reply("Название ранга не может быть пустым.")
        return
    storage.add_rank(chat_id, xp_min, name)
    await message.reply(f"Ранг '{name}' с порогом {xp_min} сообщений добавлен.")


async def cmd_ranks(message: Message) -> None:
    if message.chat.type not in group_types:
        await message.reply("Команда работает только в группах.")
        return
    chat_id = message.chat.id
    ranks = storage.list_ranks(chat_id)
    if not ranks:
        await message.reply("Для этого чата ещё нет рангов.")
        return
    lines = ["Ранги для этого чата (по количеству сообщений):"]
    for r in ranks:
        lines.append(f"{r.get('xp_min', 0)} сообщений — {r.get('name', '')}")
    await message.reply("\n".join(lines))


async def cmd_reset_ranks(message: Message, bot: Bot) -> None:
    if message.chat.type not in group_types:
        await message.reply("Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    if not await is_user_admin(bot, chat_id, user.id):
        await message.reply("Только админ чата может сбрасывать ранги.")
        return
    storage.reset_ranks(chat_id)
    await message.reply("Ранги сброшены на значения по умолчанию.")


async def cmd_setguide(message: Message, bot: Bot) -> None:
    if message.chat.type not in group_types:
        await message.reply("Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    if not await is_user_admin(bot, chat_id, user.id):
        await message.reply("Только админ чата может настраивать гайды.")
        return
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await message.reply("Использование: /setguide <ключ> <текст гайда>")
        return
    key = parts[1].strip().lower()
    text = parts[2].strip()
    if not key or not text:
        await message.reply("Ключ и текст гайда не могут быть пустыми.")
        return
    storage.set_guide(chat_id, key, text)
    await message.reply(f"Гайд '{key}' сохранён.")


async def cmd_delguide(message: Message, bot: Bot) -> None:
    if message.chat.type not in group_types:
        await message.reply("Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    if not await is_user_admin(bot, chat_id, user.id):
        await message.reply("Только админ чата может удалять гайды.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.reply("Использование: /delguide <ключ>")
        return
    key = parts[1].strip().lower()
    if not key:
        await message.reply("Ключ не может быть пустым.")
        return
    ok = storage.delete_guide(chat_id, key)
    if ok:
        await message.reply(f"Гайд '{key}' удалён.")
    else:
        await message.reply(f"Гайд с ключом '{key}' не найден.")


async def cmd_addxp(message: Message, bot: Bot) -> None:
    if message.chat.type not in group_types:
        await message.reply("Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    if not await is_user_admin(bot, chat_id, user.id):
        await message.reply("Только админ чата может выдавать сообщения другим участникам.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.reply("Использование: /addxp <количество> (команда должна быть ответом на сообщение участника)")
        return
    try:
        amount = int(parts[1].strip())
    except ValueError:
        await message.reply("Количество должно быть числом.")
        return
    if amount <= 0:
        await message.reply("Количество должно быть больше нуля.")
        return
    reply = message.reply_to_message
    if not reply or not reply.from_user or reply.from_user.is_bot:
        await message.reply("Команда должна быть ответом на сообщение участника.")
        return
    target = reply.from_user
    new_xp, old_rank, new_rank, leveled_up = storage.add_manual_xp(chat_id, target.id, amount)
    text = (
        f"Выдано {amount} очков {target.full_name or target.username}.")
    if leveled_up:
        text += f" Новый ранг: {new_rank} (всего: {new_xp})."
    else:
        text += f" Текущее количество: {new_xp}, ранг: {new_rank}."
    await message.reply(text)


async def ensure_private_chat(message: Message) -> bool:
    if message.chat.type != ChatType.PRIVATE:
        await message.reply("Эта команда доступна только в личном чате с ботом.")
        return False
    return True


async def cmd_keywords(message: Message) -> None:
    if not await ensure_private_chat(message):
        return
    keywords = storage.list_keywords()
    if not keywords:
        await message.reply("Пока нет ни одного ключевого слова.")
        return
    lines = ["Ключевые фразы, которые дают XP:"]
    for word in keywords:
        lines.append(f"• {word}")
    await message.reply("\n".join(lines))


async def cmd_addkeyword(message: Message) -> None:
    if not await ensure_private_chat(message):
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.reply("Использование: /addkeyword <фраза>")
        return
    phrase = parts[1]
    if storage.add_keyword(phrase):
        await message.reply("Фраза добавлена.")
    else:
        await message.reply("Не удалось добавить фразу (возможно, она уже есть или пуста).")


async def cmd_delkeyword(message: Message) -> None:
    if not await ensure_private_chat(message):
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.reply("Использование: /delkeyword <фраза>")
        return
    phrase = parts[1]
    if storage.delete_keyword(phrase):
        await message.reply("Фраза удалена.")
    else:
        await message.reply("Фраза не найдена.")


async def cmd_guide(message: Message) -> None:
    if message.chat.type not in group_types:
        await message.reply("Команда работает только в группах.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.reply("Использование: /guide <ключ>\nСписок ключей: /guides")
        return
    key = parts[1].strip().lower()
    chat_id = message.chat.id
    text = storage.get_guide(chat_id, key)
    if not text:
        await message.reply(
            f"Гайд с ключом '{key}' не найден. Посмотри список через /guides."
        )
        return
    await message.reply(text)


async def cmd_guides(message: Message) -> None:
    if message.chat.type not in group_types:
        await message.reply("Команда работает только в группах.")
        return
    chat_id = message.chat.id
    guides = storage.list_guides(chat_id)
    if not guides:
        await message.reply("Для этого чата ещё нет ни одного гайда.")
        return
    keyboard = build_guides_keyboard(chat_id)
    lines = ["Выбери гайд кнопкой ниже или введи /guide <ключ>:"]
    for key in sorted(guides.keys()):
        lines.append(f"• {key}")
    await message.reply("\n".join(lines), reply_markup=keyboard)
async def handle_quick_buttons(message: Message) -> bool:
    text = (message.text or "").strip().lower()
    if not text:
        return False
    if text == "поиск гайда":
        await message.reply("Напиши /guide <ключ>. Список ключей: /guides")
        return True
    if text == "список гайдов":
        await cmd_guides(message)
        return True
    if text == "мой ранг":
        await cmd_myrank(message)
        return True
    if text == "список рангов":
        await cmd_ranks(message)
        return True
    if text == "помощь":
        await cmd_help(message)
        return True
    return False


async def handle_guide_callback(callback: CallbackQuery) -> None:
    data = callback.data or ""
    if not data.startswith(GUIDE_CALLBACK_PREFIX):
        return
    key = data[len(GUIDE_CALLBACK_PREFIX) :]
    message = callback.message
    if message is None:
        await callback.answer("Сообщение не найдено", show_alert=True)
        return
    chat_id = message.chat.id
    text = storage.get_guide(chat_id, key)
    if text:
        await callback.answer()
        sent = await message.answer(text)
        bot = message.bot
        asyncio.create_task(
            schedule_delete_message(bot, sent.chat.id, sent.message_id)
        )
    else:
        await callback.answer("Гайд не найден", show_alert=True)


async def on_reaction(update: MessageReactionUpdated) -> None:
    chat = update.chat
    if chat.type not in group_types:
        return
    user = update.user
    if user is None or user.is_bot:
        return
    new_reactions = update.new_reaction or []
    old_reactions = update.old_reaction or []
    if len(new_reactions) <= len(old_reactions):
        return
    chat_id = chat.id
    user_id = user.id
    now_ts = int(time.time())
    new_xp, old_rank, new_rank, leveled_up = storage.add_message_xp(
        chat_id, user_id, now_ts
    )
    if leveled_up:
        name = user.full_name or user.username or "участник"
        await update.bot.send_message(
            chat_id,
            f"{name}, поздравляю! Твой новый ранг: {new_rank} (очков: {new_xp}).",
        )


async def on_message(message: Message) -> None:
    if message.chat.type not in group_types:
        return
    user = message.from_user
    if user is None or user.is_bot:
        return
    if not message.text or message.text.startswith("/"):
        return
    handled = await handle_quick_buttons(message)
    if handled:
        return
    if not is_help_request(message.text):
        return
    chat_id = message.chat.id
    user_id = user.id
    now_ts = int(time.time())
    new_xp, old_rank, new_rank, leveled_up = storage.add_message_xp(
        chat_id, user_id, now_ts
    )
    if leveled_up:
        name = user.full_name or user.username or "участник"
        await message.reply(
            f"{name}, поздравляю! Твой новый ранг: {new_rank} (сообщений: {new_xp})."
        )


async def main() -> None:
    if not config.BOT_TOKEN or config.BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        raise RuntimeError("Сначала укажи токен бота в файле config.py (BOT_TOKEN).")
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="help", description="Список команд"),
            BotCommand(command="myrank", description="Показать мой ранг"),
            BotCommand(command="ranks", description="Список рангов"),
            BotCommand(command="guides", description="Список гайдов"),
            BotCommand(command="guide", description="Показать гайд по ключу"),
        ]
    )

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_myrank, Command("myrank"))
    dp.message.register(cmd_addrank, Command("addrank"))
    dp.message.register(cmd_addxp, Command("addxp"))
    dp.message.register(cmd_ranks, Command("ranks"))
    dp.message.register(cmd_reset_ranks, Command("resetranks"))
    dp.message.register(cmd_setguide, Command("setguide"))
    dp.message.register(cmd_delguide, Command("delguide"))
    dp.message.register(cmd_guide, Command("guide"))
    dp.message.register(cmd_guides, Command("guides"))
    dp.message.register(cmd_keywords, Command("keywords"))
    dp.message.register(cmd_addkeyword, Command("addkeyword"))
    dp.message.register(cmd_delkeyword, Command("delkeyword"))
    dp.message.register(on_message)
    dp.callback_query.register(handle_guide_callback)
    dp.message_reaction.register(on_reaction)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
