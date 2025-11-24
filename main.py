from __future__ import annotations


RELEASES_PAGE_SIZE = 3
RELEASES_CALLBACK_PREFIX = "rel:"


def format_datetime(iso_str: str | None) -> str:
    if not iso_str:
        return "-"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except ValueError:
        return iso_str
    return dt.strftime("%d.%m.%Y %H:%M UTC")


def format_date_short(iso_str: str | None) -> str:
    if not iso_str:
        return "-"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except ValueError:
        return "-"
    return dt.strftime("%d.%m.%Y")


async def fetch_latest_release(session: aiohttp.ClientSession) -> dict | None:
    url = f"https://api.github.com/repos/{config.GITHUB_REPO}/releases"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ryazhenka-helper-bot/1.0",
    }
    async with session.get(url, headers=headers, timeout=30) as resp:
        if resp.status != 200:
            text = await resp.text()
            logger.warning("Failed to fetch releases: %s - %s", resp.status, text)
            return None
        data = await resp.json()
    if not data:
        return None
    return data[0]


def build_release_summary(release: dict, changes: list[str] | None = None) -> str:
    tag = release.get("tag_name") or release.get("name") or "?"
    name = release.get("name") or "Без названия"
    published = format_datetime(release.get("published_at"))
    url = release.get("html_url") or release.get("url") or ""
    lines = [
        "🥛 Вышла новая прошивка Ryazhenka!",
        f"Tag: {tag}",
        f"Название: {name}",
        f"Дата: {published}",
    ]
    if url:
        lines.append(f"Ссылка: {url}")
    body = release.get("body")
    if changes:
        lines.append("\nИзменения:\n" + "\n".join(changes))
    elif body:
        trimmed = body.strip()
        if trimmed:
            lines.append("\nОписание:\n" + trimmed)
    return "\n".join(lines)


def build_release_changes(
    previous_body: str | None, current_body: str | None
) -> list[str]:
    if not current_body:
        return []
    limit = int(getattr(config, "RELEASE_DIFF_LIMIT", 0) or 0)
    current_lines = [line.rstrip() for line in current_body.strip().splitlines()]
    if limit <= 0:
        return [line for line in current_lines if line][:15]
    if not previous_body:
        return [line for line in current_lines if line][:limit]
    previous_lines = [line.rstrip() for line in previous_body.strip().splitlines()]
    diff = difflib.unified_diff(previous_lines, current_lines, lineterm="")
    changes: list[str] = []
    for line in diff:
        if line.startswith(("---", "+++", "@@")):
            continue
        if line.startswith("+") and not line.startswith("++"):
            content = line[1:].strip()
            if content:
                changes.append(f"+ {content}")
        elif line.startswith("-") and not line.startswith("--"):
            content = line[1:].strip()
            if content:
                changes.append(f"- {content}")
        if len(changes) >= limit:
            break
    if not changes:
        return [line for line in current_lines if line][:limit]
    return changes


async def fetch_releases(session: aiohttp.ClientSession, limit: int = 30) -> list[dict]:
    url = f"https://api.github.com/repos/{config.GITHUB_REPO}/releases"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ryazhenka-helper-bot/1.0",
    }
    params = {"per_page": max(limit, 1)}
    async with session.get(url, headers=headers, params=params, timeout=30) as resp:
        if resp.status != 200:
            text = await resp.text()
            logger.warning("Failed to fetch releases list: %s - %s", resp.status, text)
            return []
        data = await resp.json()
    if not isinstance(data, list):
        return []
    return data[:limit]


def simplify_release(release: dict) -> dict:
    return {
        "id": release.get("id"),
        "tag_name": release.get("tag_name"),
        "name": release.get("name"),
        "html_url": release.get("html_url") or release.get("url"),
        "published_at": release.get("published_at"),
        "body": release.get("body"),
    }


async def get_release_list(force: bool = False) -> list[dict]:
    if aiohttp is None:
        logger.warning("aiohttp is not installed; cannot fetch release list")
        return []
    cached, fetched_at = storage.get_release_list()
    ttl = int(getattr(config, "RELEASE_LIST_TTL_SECONDS", 900) or 900)
    now = time.time()
    if cached and not force and now - fetched_at < ttl:
        return cached
    async with aiohttp.ClientSession() as session:
        releases = await fetch_releases(session)
    if releases:
        simplified = [simplify_release(release) for release in releases]
        storage.set_release_list(simplified)
        return simplified
    return cached


def format_release_button_label(release: dict) -> str:
    tag = release.get("tag_name") or release.get("name") or "?"
    date = format_date_short(release.get("published_at"))
    return f"{tag} · {date}" if date != "-" else tag


def build_release_list_keyboard(releases: list[dict], offset: int = 0) -> InlineKeyboardMarkup:
    offset = max(0, offset)
    total = len(releases)
    end = min(offset + RELEASES_PAGE_SIZE, total)
    buttons: list[list[InlineKeyboardButton]] = []
    for idx in range(offset, end):
        release = releases[idx]
        label = format_release_button_label(release)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label[:64],
                    callback_data=f"{RELEASES_CALLBACK_PREFIX}item:{idx}",
                )
            ]
        )
    nav_row: list[InlineKeyboardButton] = []
    if offset > 0:
        prev_offset = max(offset - RELEASES_PAGE_SIZE, 0)
        nav_row.append(
            InlineKeyboardButton(
                text="◀ Назад",
                callback_data=f"{RELEASES_CALLBACK_PREFIX}page:{prev_offset}",
            )
        )
    if end < total:
        nav_row.append(
            InlineKeyboardButton(
                text="Ещё",
                callback_data=f"{RELEASES_CALLBACK_PREFIX}page:{end}",
            )
        )
    if nav_row:
        buttons.append(nav_row)
    if not buttons:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Обновить",
                    callback_data=f"{RELEASES_CALLBACK_PREFIX}page:0",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


RELEASE_DETAIL_BODY_LINES = 15


def format_release_detail(release: dict) -> str:
    tag = release.get("tag_name") or release.get("name") or "?"
    name = release.get("name") or "Без названия"
    published = format_datetime(release.get("published_at"))
    url = release.get("html_url") or release.get("url") or ""
    lines = [
        "🥛 Релиз Ryazhenka",
        f"Tag: {tag}",
        f"Название: {name}",
        f"Дата: {published}",
    ]
    if url:
        lines.append(f"Ссылка: {url}")
    body = release.get("body")
    if body:
        trimmed = body.strip()
        if trimmed:
            body_lines = trimmed.splitlines()
            snippet = "\n".join(body_lines[:RELEASE_DETAIL_BODY_LINES]).strip()
            if len(body_lines) > RELEASE_DETAIL_BODY_LINES:
                snippet += "\n..."
            if snippet:
                lines.append("\nОписание:\n" + snippet)
    return "\n".join(lines)


async def send_release_list_message(
    message: Message,
    *,
    offset: int = 0,
    force: bool = False,
    edit_message: Message | None = None,
) -> None:
    if aiohttp is None:
        text = "Список релизов недоступен: не установлен aiohttp."
        if edit_message:
            try:
                await edit_message.edit_text(text)
            except TelegramBadRequest:
                await edit_message.edit_reply_markup()
        else:
            await reply_with_cleanup(message, text, auto_delete=False)
        return
    try:
        releases = await get_release_list(force=force)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load release list: %s", exc)
        await reply_with_cleanup(
            message,
            "Не удалось получить список релизов. Попробуй позже.",
        )
        return
    if not releases:
        text = "Не удалось получить список релизов. Попробуй позже."
        if edit_message:
            try:
                await edit_message.edit_text(text)
            except TelegramBadRequest:
                await edit_message.edit_reply_markup()
        else:
            await reply_with_cleanup(message, text)
        return
    keyboard = build_release_list_keyboard(releases, offset)
    text = "Последние релизы Ryazhenka:"
    if edit_message:
        try:
            await edit_message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest:
            await edit_message.edit_reply_markup(reply_markup=keyboard)
    else:
        await reply_with_cleanup(
            message,
            text,
            reply_markup=keyboard,
            auto_delete=False,
        )


async def broadcast_release(bot: Bot, summary: str) -> None:
    chat_ids = storage.list_chat_ids()
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, summary)
        except TelegramForbiddenError:
            logger.info("Skipping chat %s: bot has no permission", chat_id)
        except TelegramBadRequest as exc:
            logger.warning("Failed to send release to %s: %s", chat_id, exc)


async def refresh_release_info(
    bot: Bot | None = None, force: bool = False, broadcast: bool = False
) -> tuple[str | None, bool]:
    if aiohttp is None:
        logger.warning("aiohttp is not installed; release info unavailable")
        return None, False
    async with aiohttp.ClientSession() as session:
        release = await fetch_latest_release(session)
        if not release:
            return None, False
        tag = release.get("tag_name") or release.get("name")
        last_tag, _, cached_summary, last_body = storage.get_last_release_info()
        new_release = tag and tag != last_tag
        current_body = release.get("body")
        changes: list[str] | None = None
        if new_release or force:
            changes = build_release_changes(last_body, current_body)
        if not new_release and not force:
            return cached_summary, False
        summary = build_release_summary(release, changes if changes else None)
        storage.set_last_release_info(
            tag or "",
            release.get("published_at"),
            summary,
            current_body,
        )
        should_broadcast = broadcast and new_release and last_tag is not None
        if should_broadcast and bot:
            await broadcast_release(bot, summary)
        return summary, new_release


async def release_monitor(bot: Bot) -> None:
    if aiohttp is None:
        logger.warning("Release monitor disabled: aiohttp not installed")
        return
    await asyncio.sleep(10)
    interval = getattr(config, "RELEASE_CHECK_INTERVAL_SECONDS", 600)
    while True:
        try:
            await refresh_release_info(bot=bot, broadcast=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Release monitor error: %s", exc)
        await asyncio.sleep(interval)
import asyncio
import difflib
import logging
import re
import time
from contextlib import suppress
from datetime import datetime

try:
    import aiohttp
except ImportError:  # pragma: no cover - optional dependency
    aiohttp = None
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
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

PROJECTS_RYAZHENKA_TEXT = (
    "Проекты Ryazhenka:\n"
    "Выбери репозиторий на клавиатуре ниже, чтобы открыть его страницу."
)

PROJECTS_RYAZHENKA_LINKS = [
    (
        "Ryazhahand Overlay",
        "https://github.com/Dimasick-git/Ryazhahand-Overlay",
    ),
    (
        "Ryazhenkabestcfw Tuner",
        "https://github.com/Dimasick-git/Ryazhenkabestcfw-Tuner",
    ),
    (
        "RyazhaTune",
        "https://github.com/Dimasick-git/RyazhaTune",
    ),
    (
        "Ryazha Status Monitor",
        "https://github.com/Dimasick-git/Ryazha-Status-Monitor",
    ),
]


logger = logging.getLogger(__name__)


AUTO_DELETE_DELAY = int(getattr(config, "BOT_MESSAGE_TTL_SECONDS", 180))


async def schedule_delete_message(bot: Bot, chat_id: int, message_id: int, delay: int = 300) -> None:
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass
    except Exception:
        pass


def _schedule_auto_delete(sent: Message, *, auto_delete: bool = True, delay: int | None = None) -> None:
    if not auto_delete:
        return
    if sent.chat.type not in group_types:
        return
    ttl = AUTO_DELETE_DELAY if delay is None else delay
    if ttl <= 0:
        return
    asyncio.create_task(
        schedule_delete_message(sent.bot, sent.chat.id, sent.message_id, ttl)
    )


async def reply_with_cleanup(
    message: Message,
    text: str,
    *,
    auto_delete: bool = True,
    delay: int | None = None,
    **kwargs,
) -> Message:
    sent = await message.reply(text, **kwargs)
    _schedule_auto_delete(sent, auto_delete=auto_delete, delay=delay)
    return sent


async def answer_with_cleanup(
    message: Message,
    text: str,
    *,
    auto_delete: bool = True,
    delay: int | None = None,
    **kwargs,
) -> Message:
    sent = await message.answer(text, **kwargs)
    _schedule_auto_delete(sent, auto_delete=auto_delete, delay=delay)
    return sent


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
                KeyboardButton(text="Проекты Ryazhenka"),
                KeyboardButton(text="Релизы"),
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


def build_projects_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=name, url=url)]
        for name, url in PROJECTS_RYAZHENKA_LINKS
    ]
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
        user = message.from_user
        if user is None:
            return
        if not await is_user_admin(bot, message.chat.id, user.id):
            return
        await reply_with_cleanup(
            message,
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
        await answer_with_cleanup(
            message,
            "Привет! Я Ruzhenka-helper — бот для групп.\n"
            "Добавь меня в свой чат как админа и используй /help в чате.",
            reply_markup=keyboard,
        )
        await answer_with_cleanup(
            message,
            "Выбери действие на клавиатуре ниже.",
            reply_markup=make_main_keyboard(),
        )


async def cmd_help(message: Message) -> None:
    text = (
        "Команды Ruzhenka-helper:\n"
        "/myrank – показать твой ранг и количество сообщений\n"
        "/guide <ключ> – показать гайд\n"
        "/guides – список гайдов\n\n"
        "Обновления прошивки:\n"
        "/release – текущий релиз Ryazhenka\n\n"
        "Только админы группы:\n"
        "/addrank <сообщений> <название> – добавить ранг (порог по сообщениям)\n"
        "/ranks – список рангов и их пороги\n"
        "/resetranks <кол-во> (в ответ на сообщение) – снять сообщения/ранг\n"
        "/setguide <ключ> <текст> – создать/обновить гайд\n"
        "/delguide <ключ> – удалить гайд\n"
        "/addxp <кол-во> (в ответ на сообщение) – вручную выдать сообщения/ранг\n"
        "/leavebot – удалить бота из чата\n\n"
        "Только в личном чате с ботом:\n"
        "/keywords – показать ключевые фразы\n"
        "/addkeyword <фраза> – добавить фразу\n"
        "/delkeyword <фраза> – удалить фразу\n"
    )
    await reply_with_cleanup(message, text)


async def cmd_myrank(message: Message) -> None:
    if message.chat.type not in group_types:
        await reply_with_cleanup(message, "Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    user_id = user.id
    user_data = storage.get_user(chat_id, user_id, user.username)
    xp = int(user_data.get("xp", 0))
    rank = storage.get_rank_for_xp(chat_id, xp)
    await reply_with_cleanup(message, f"Твой ранг: {rank}\nСообщений: {xp}")


async def cmd_addrank(message: Message, bot: Bot) -> None:
    if message.chat.type not in group_types:
        await reply_with_cleanup(message, "Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    if not await is_user_admin(bot, chat_id, user.id):
        await reply_with_cleanup(message, "Только админ чата может настраивать ранги.")
        return
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await reply_with_cleanup(
            message,
            "Использование: /addrank <сообщений_минимум> <название ранга>"
        )
        return
    try:
        xp_min = int(parts[1])
    except ValueError:
        await reply_with_cleanup(message, "Количество сообщений должно быть числом.")
        return
    name = parts[2].strip()
    if not name:
        await reply_with_cleanup(message, "Название ранга не может быть пустым.")
        return
    storage.add_rank(chat_id, xp_min, name)
    await reply_with_cleanup(
        message, f"Ранг '{name}' с порогом {xp_min} сообщений добавлен."
    )


async def cmd_ranks(message: Message) -> None:
    if message.chat.type not in group_types:
        await reply_with_cleanup(message, "Команда работает только в группах.")
        return
    chat_id = message.chat.id
    ranks = storage.list_ranks(chat_id)
    if not ranks:
        await reply_with_cleanup(message, "Для этого чата ещё нет рангов.")
        return
    lines = ["Ранги для этого чата (по количеству сообщений):"]
    for r in ranks:
        lines.append(f"{r.get('xp_min', 0)} сообщений — {r.get('name', '')}")
    await reply_with_cleanup(message, "\n".join(lines))


async def cmd_reset_ranks(message: Message, bot: Bot) -> None:
    if message.chat.type not in group_types:
        await reply_with_cleanup(message, "Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    if not await is_user_admin(bot, chat_id, user.id):
        await reply_with_cleanup(
            message, "Только админ чата может снимать очки у участников."
        )
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await reply_with_cleanup(
            message,
            "Использование: /resetranks <количество> (команда должна быть ответом на сообщение участника)",
        )
        return
    try:
        amount = int(parts[1].strip())
    except ValueError:
        await reply_with_cleanup(message, "Количество должно быть числом.")
        return
    if amount <= 0:
        await reply_with_cleanup(message, "Количество должно быть больше нуля.")
        return
    reply = message.reply_to_message
    if not reply or not reply.from_user or reply.from_user.is_bot:
        await reply_with_cleanup(
            message, "Команда должна быть ответом на сообщение участника."
        )
        return
    target = reply.from_user
    new_xp, old_rank, new_rank, leveled_up = storage.add_manual_xp(
        chat_id, target.id, target.username, -amount
    )
    text = (
        f"Снято {amount} очков у {target.full_name or target.username}.")
    if leveled_up:
        text += f" Новый ранг: {new_rank} (всего: {new_xp})."
    else:
        text += f" Текущее количество: {new_xp}, ранг: {new_rank}."
    await reply_with_cleanup(message, text)


async def cmd_setguide(message: Message, bot: Bot) -> None:
    if message.chat.type not in group_types:
        await reply_with_cleanup(message, "Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    if not await is_user_admin(bot, chat_id, user.id):
        await reply_with_cleanup(message, "Только админ чата может настраивать гайды.")
        return
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await reply_with_cleanup(message, "Использование: /setguide <ключ> <текст гайда>")
        return
    key = parts[1].strip().lower()
    text = parts[2].strip()
    if not key or not text:
        await reply_with_cleanup(message, "Ключ и текст гайда не могут быть пустыми.")
        return
    storage.set_guide(chat_id, key, text)
    await reply_with_cleanup(message, f"Гайд '{key}' сохранён.")


async def cmd_delguide(message: Message, bot: Bot) -> None:
    if message.chat.type not in group_types:
        await reply_with_cleanup(message, "Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    if not await is_user_admin(bot, chat_id, user.id):
        await reply_with_cleanup(message, "Только админ чата может удалять гайды.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await reply_with_cleanup(message, "Использование: /delguide <ключ>")
        return
    key = parts[1].strip().lower()
    if not key:
        await reply_with_cleanup(message, "Ключ не может быть пустым.")
        return
    ok = storage.delete_guide(chat_id, key)
    if ok:
        await reply_with_cleanup(message, f"Гайд '{key}' удалён.")
    else:
        await reply_with_cleanup(
            message, f"Гайд с ключом '{key}' не найден."
        )


async def cmd_leavebot(message: Message, bot: Bot) -> None:
    if message.chat.type not in group_types:
        await reply_with_cleanup(message, "Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    if not await is_user_admin(bot, chat_id, user.id):
        await reply_with_cleanup(message, "Только админ чата может удалить бота.")
        return
    await reply_with_cleanup(
        message,
        "Хорошо, ухожу из чата. Всегда можно добавить меня снова! 👋",
        auto_delete=False,
    )
    await bot.leave_chat(chat_id)


async def cmd_addxp(message: Message, bot: Bot) -> None:
    if message.chat.type not in group_types:
        await reply_with_cleanup(message, "Команда работает только в группах.")
        return
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id
    if not await is_user_admin(bot, chat_id, user.id):
        await reply_with_cleanup(
            message,
            "Только админ чата может выдавать сообщения другим участникам.",
        )
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await reply_with_cleanup(
            message,
            "Использование: /addxp <количество> (команда должна быть ответом на сообщение участника)",
        )
        return
    try:
        amount = int(parts[1].strip())
    except ValueError:
        await reply_with_cleanup(message, "Количество должно быть числом.")
        return
    if amount <= 0:
        await reply_with_cleanup(message, "Количество должно быть больше нуля.")
        return
    reply = message.reply_to_message
    if not reply or not reply.from_user or reply.from_user.is_bot:
        await reply_with_cleanup(
            message, "Команда должна быть ответом на сообщение участника."
        )
        return
    target = reply.from_user
    new_xp, old_rank, new_rank, leveled_up = storage.add_manual_xp(
        chat_id, target.id, target.username, amount
    )
    text = (
        f"Выдано {amount} очков {target.full_name or target.username}.")
    if leveled_up:
        text += f" Новый ранг: {new_rank} (всего: {new_xp})."
    else:
        text += f" Текущее количество: {new_xp}, ранг: {new_rank}."
    await reply_with_cleanup(message, text)


async def ensure_private_chat(message: Message) -> bool:
    if message.chat.type != ChatType.PRIVATE:
        await reply_with_cleanup(
            message, "Эта команда доступна только в личном чате с ботом."
        )
        return False
    return True


async def cmd_keywords(message: Message) -> None:
    if not await ensure_private_chat(message):
        return
    keywords = storage.list_keywords()
    if not keywords:
        await reply_with_cleanup(message, "Пока нет ни одного ключевого слова.")
        return
    lines = ["Ключевые фразы, которые дают XP:"]
    for word in keywords:
        lines.append(f"• {word}")
    await reply_with_cleanup(message, "\n".join(lines))


async def cmd_addkeyword(message: Message) -> None:
    if not await ensure_private_chat(message):
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await reply_with_cleanup(message, "Использование: /addkeyword <фраза>")
        return
    phrase = parts[1]
    if storage.add_keyword(phrase):
        await reply_with_cleanup(message, "Фраза добавлена.")
    else:
        await reply_with_cleanup(
            message,
            "Не удалось добавить фразу (возможно, она уже есть или пуста).",
        )


async def cmd_delkeyword(message: Message) -> None:
    if not await ensure_private_chat(message):
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await reply_with_cleanup(message, "Использование: /delkeyword <фраза>")
        return
    phrase = parts[1]
    if storage.delete_keyword(phrase):
        await reply_with_cleanup(message, "Фраза удалена.")
    else:
        await reply_with_cleanup(message, "Фраза не найдена.")


async def cmd_release(message: Message) -> None:
    if aiohttp is None:
        await reply_with_cleanup(
            message,
            "Модуль aiohttp не установлен. Установи зависимости (`pip install -r requirements.txt`), и я смогу показывать релизы."
        )
        return
    args = message.text.split(maxsplit=1) if message.text else []
    force = False
    if len(args) > 1:
        force = args[1].strip().lower() in {"refresh", "update", "force"}
    summary = None
    if force:
        summary, _ = await refresh_release_info(force=True)
    else:
        _, _, cached, _ = storage.get_last_release_info()
        summary = cached
        if not summary:
            summary, _ = await refresh_release_info(force=True)
    if summary:
        await reply_with_cleanup(message, summary, auto_delete=False)
    else:
        await reply_with_cleanup(
            message, "Информация о релизах пока недоступна. Попробуй позже."
        )


async def cmd_guide(message: Message) -> None:
    if message.chat.type not in group_types:
        await reply_with_cleanup(message, "Команда работает только в группах.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await reply_with_cleanup(
            message, "Использование: /guide <ключ>\nСписок ключей: /guides"
        )
        return
    key = parts[1].strip().lower()
    chat_id = message.chat.id
    text = storage.get_guide(chat_id, key)
    if not text:
        await reply_with_cleanup(
            message,
            f"Гайд с ключом '{key}' не найден. Посмотри список через /guides.",
        )
        return
    await reply_with_cleanup(message, text, auto_delete=False)


async def cmd_guides(message: Message) -> None:
    if message.chat.type not in group_types:
        await reply_with_cleanup(message, "Команда работает только в группах.")
        return
    chat_id = message.chat.id
    guides = storage.list_guides(chat_id)
    if not guides:
        await reply_with_cleanup(message, "Для этого чата ещё нет ни одного гайда.")
        return
    keyboard = build_guides_keyboard(chat_id)
    lines = ["Выбери гайд кнопкой ниже или введи /guide <ключ>:"]
    for key in sorted(guides.keys()):
        lines.append(f"• {key}")
    await reply_with_cleanup(
        message,
        "\n".join(lines),
        reply_markup=keyboard,
        auto_delete=False,
    )


async def handle_guide_callback(callback: CallbackQuery) -> None:
    data = callback.data or ""
    if not data.startswith(GUIDE_CALLBACK_PREFIX):
        return
    await callback.answer()
    message = callback.message
    if message is None:
        return
    chat_id = message.chat.id
    key = data[len(GUIDE_CALLBACK_PREFIX) :]
    if not key:
        return
    text = storage.get_guide(chat_id, key)
    if not text:
        try:
            await message.edit_text(
                "Гайд не найден. Обнови список /guides.", reply_markup=None
            )
        except TelegramBadRequest:
            await message.edit_reply_markup()
        return
    await reply_with_cleanup(
        message,
        text,
        auto_delete=False,
    )


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
        chat_id, user_id, user.username, now_ts
    )
    if leveled_up:
        name = user.full_name or user.username or "участник"
        await update.bot.send_message(
            chat_id,
            f"{name}, поздравляю! Твой новый ранг: {new_rank} (очков: {new_xp}).",
        )


async def on_message(message: Message) -> None:
    user = message.from_user
    if user is None or user.is_bot:
        return
    if not message.text or message.text.startswith("/"):
        return
    handled = await handle_quick_buttons(message)
    if handled:
        return
    if message.chat.type not in group_types:
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
        await reply_with_cleanup(
            message,
            f"{name}, поздравляю! Твой новый ранг: {new_rank} (сообщений: {new_xp}).",
            auto_delete=False,
        )


async def handle_release_callback(callback: CallbackQuery) -> None:
    data = callback.data or ""
    if not data.startswith(RELEASES_CALLBACK_PREFIX):
        return
    await callback.answer()
    payload = data[len(RELEASES_CALLBACK_PREFIX) :]
    parts = payload.split(":", 1)
    if len(parts) != 2:
        return
    action, value = parts
    message = callback.message
    if message is None:
        return
    releases = await get_release_list()
    if not releases:
        try:
            await message.edit_text("Список релизов недоступен. Попробуй позже.")
        except TelegramBadRequest:
            await message.edit_reply_markup()
        return
    if action == "page":
        try:
            offset = int(value)
        except ValueError:
            offset = 0
        await send_release_list_message(
            message,
            offset=offset,
            edit_message=message,
        )
    elif action == "item":
        try:
            index = int(value)
        except ValueError:
            index = 0
        if 0 <= index < len(releases):
            detail = format_release_detail(releases[index])
            await reply_with_cleanup(
                message,
                detail,
                auto_delete=False,
            )


async def handle_quick_buttons(message: Message) -> bool:
    text = (message.text or "").strip()
    if not text:
        return False
    if text == "Поиск гайда":
        await reply_with_cleanup(
            message,
            "Напиши /guide <ключ> или воспользуйся кнопками /guides.",
        )
        return True
    if text == "Список гайдов":
        keyboard = build_guides_keyboard(message.chat.id)
        if keyboard is None:
            await reply_with_cleanup(
                message,
                "Пока нет сохранённых гайдов. Добавь их через /setguide.",
            )
        else:
            await reply_with_cleanup(
                message,
                "Выбери гайд из списка или используй /guide <ключ>:",
                reply_markup=keyboard,
                auto_delete=False,
            )
        return True
    if text == "Мой ранг":
        await cmd_myrank(message)
        return True
    if text == "Список рангов":
        await cmd_ranks(message)
        return True
    if text == "Помощь":
        await cmd_help(message)
        return True
    if text == "Проекты Ryazhenka":
        await reply_with_cleanup(
            message,
            PROJECTS_RYAZHENKA_TEXT,
            reply_markup=build_projects_keyboard(),
            auto_delete=False,
        )
        return True
    if text == "Релизы":
        placeholder = await reply_with_cleanup(
            message,
            "Загружаю список релизов...",
            auto_delete=False,
        )
        await send_release_list_message(
            message,
            force=False,
            edit_message=placeholder,
        )
        return True
    return False


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
            BotCommand(command="release", description="Последний релиз Ryazhenka"),
        ]
    )

    release_task = None
    if aiohttp is not None:
        release_task = asyncio.create_task(release_monitor(bot))

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_myrank, Command("myrank"))
    dp.message.register(cmd_addrank, Command("addrank"))
    dp.message.register(cmd_addxp, Command("addxp"))
    dp.message.register(cmd_ranks, Command("ranks"))
    dp.message.register(cmd_reset_ranks, Command("resetranks"))
    dp.message.register(cmd_setguide, Command("setguide"))
    dp.message.register(cmd_delguide, Command("delguide"))
    dp.message.register(cmd_leavebot, Command("leavebot"))
    dp.message.register(cmd_guide, Command("guide"))
    dp.message.register(cmd_guides, Command("guides"))
    dp.message.register(cmd_release, Command("release"))
    dp.message.register(cmd_keywords, Command("keywords"))
    dp.message.register(cmd_addkeyword, Command("addkeyword"))
    dp.message.register(cmd_delkeyword, Command("delkeyword"))
    dp.message.register(on_message)
    dp.callback_query.register(
        handle_guide_callback, F.data.startswith(GUIDE_CALLBACK_PREFIX)
    )
    dp.callback_query.register(
        handle_release_callback, F.data.startswith(RELEASES_CALLBACK_PREFIX)
    )
    dp.message_reaction.register(on_reaction)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        if release_task:
            release_task.cancel()
            with suppress(asyncio.CancelledError):
                await release_task


if __name__ == "__main__":
    asyncio.run(main())
