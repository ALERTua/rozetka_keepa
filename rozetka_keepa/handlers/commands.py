from __future__ import annotations

import re
from copy import copy

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.text_decorations import HtmlDecoration, MarkdownDecoration
from rozetka.entities.item import Item

from rozetka_keepa import constants, tools
from rozetka_keepa.db import DBController
from rozetka_keepa.models.callbacks import GetItemCallback, RemoveItemCallback

ITEM_CMD = "/item"
USAGE = f"Usage: {ITEM_CMD} ID PRICE"
REGISTER = "/start"
REGISTER_USAGE = f"Use {REGISTER} to register"

router = Router()
dbc = DBController.instantiate()

html = HtmlDecoration()
md = MarkdownDecoration()


@router.message(CommandStart())
async def start(message: Message):
    telegram_id = message.from_user.id
    kwargs = dict(telegram_id=telegram_id)
    exists = dbc.get_user(**kwargs)
    if exists:
        await message.reply("You are already registered.")
        return

    dbc.create_user(**kwargs)
    dbc.commit()
    await message.reply("You are now registered.")


@router.message(Command("deleteme"))
async def deleteme(message: Message):
    telegram_id = message.from_user.id
    kwargs = dict(telegram_id=telegram_id)
    exists = dbc.get_user(**kwargs)
    if not exists:
        await message.reply("Your user does not exist.")
        return

    user = exists[0]
    dbc.delete_user(user)
    await message.reply("Your user is removed.")


async def remove_item(item_id: int, msg: CallbackQuery | Message):
    message = msg if isinstance(msg, Message) else msg.message
    kwargs = dict(telegram_id=msg.from_user.id)
    exists = dbc.get_user(**kwargs)
    if not exists:
        await message.reply(text=f"Your user does not exist.\n{REGISTER_USAGE}")
        return

    user = exists[0]

    existing = dbc.get_user_item_id(user, item_id=item_id)
    if not existing:
        await message.reply(text=f"You didn't add an item ID {item_id} or item doesn't exist\n{USAGE}")
        return

    item = existing[0]
    dbc.remove_item(item)
    await message.reply(text=f"Item {item} removed from watched list")


@router.callback_query(RemoveItemCallback.filter())
async def remove_item_callback(query: CallbackQuery, callback_data: RemoveItemCallback):
    await remove_item(callback_data.item_id, query)


@router.message(Command("remove"))
async def remove_item_command(message: Message | CallbackQuery):  # /remove 123
    cmd = "/remove"
    text = message.text or message.data
    obj = text.replace(f"{cmd} ", "")  # 123
    if not re.match(r"\d+", obj):
        await message.reply(f"Usage: {cmd} ID")
        return

    item_id = int(obj)
    await remove_item(item_id, message)


async def get_item(item_id: int, msg: CallbackQuery | Message, price_str=None):
    message = msg if isinstance(msg, Message) else msg.message
    telegram_id = message.from_user.id
    kwargs = dict(telegram_id=telegram_id)
    exists = dbc.get_user(**kwargs)
    if not exists:
        return await message.reply(f"Your user does not exist.\n{REGISTER_USAGE}")

    user = exists[0]
    existing = None
    if price_str is None:
        existing = dbc.get_user_item_id(user, item_id=item_id)
        if not existing:
            return await message.reply(f"You didn't add an item ID {item_id}\n{USAGE}")

        item = existing[0]
        keepa = item.item
        # noinspection PyProtectedMember
        if not keepa._parsed:  # noqa: SLF001
            temp_message = await message.reply("One moment. Parsing item", disable_notification=True)
            keepa.parse()
            await temp_message.delete()

        image = keepa.image_main
        href = keepa.href
        msg = f"""
{html.link(str(item_id), href)} {keepa.title}
Wanted: {item.wanted_price}
Current: {keepa.price}
Added @ {item.added}
"""
        builder = InlineKeyboardBuilder()
        builder.button(text="Page", url=href)
        remove_watch_callback_data = RemoveItemCallback(item_id=item_id).pack()
        builder.button(text="Remove Watch", callback_data=remove_watch_callback_data)
        if image:
            await message.reply_photo(
                photo=image,
                caption=msg,
                parse_mode=ParseMode.HTML,
                allow_sending_without_reply=True,
                reply_markup=builder.as_markup(),
            )
        else:
            await message.reply(
                text=msg,
                parse_mode=ParseMode.HTML,
                allow_sending_without_reply=True,
                reply_markup=builder.as_markup(),
            )
        return None

    if (price := tools.float_from_str(price_str)) is None:
        return await message.reply("Please provide an integer or float price.")

    existing = existing if existing is not None else dbc.get_user_item_id(user, item_id=item_id)
    if existing:
        item = existing[0]
        if item.wanted_price == price:
            return await message.reply(f"{item} wanted price is already @ {price}. It was added @ {item.added}")

        old_price = copy(item.wanted_price)
        item.wanted_price = price
        dbc.commit()
        return await message.reply(f"{item} price changed from {old_price} to {price}")

    item = dbc.user_add_item(user=user, item_id=item_id, wanted_price=price)
    await message.reply(f"Item {item} added")
    return None


@router.callback_query(GetItemCallback.filter())
async def get_item_callback(query: CallbackQuery, callback_data: RemoveItemCallback):
    await get_item(callback_data.item_id, query)


@router.message(Command("item"))
async def add_edit_item(message: Message):
    obj = message.text.replace(f"{ITEM_CMD} ", "")  # /item 123 12.99
    obj_split = obj.split(" ")  # ['123', '12.99']
    if len(obj_split) == 1:  # ['123']
        item_id = obj_split[0]
        price_str = None
    elif len(obj_split) != 2:  # noqa: PLR2004
        return await message.reply(USAGE)
    else:
        item_id, price_str = obj_split  # '123' '12.99'

    if not re.match(r"\d+", item_id):
        return await message.reply(USAGE)

    item_id = int(item_id)

    await get_item(item_id, message, price_str=price_str)
    return None


@router.message(Command(BotCommand(command="list", description="items list")))
@router.message(Command(BotCommand(command="items", description="items list")))
async def list_(message: Message):
    telegram_id = message.from_user.id
    kwargs = dict(telegram_id=telegram_id)
    exists = dbc.get_user(**kwargs)
    if not exists:
        return await message.reply(f"Your user does not exist.\n{REGISTER_USAGE}")

    user = exists[0]

    items = dbc.get_user_items(user)
    if not items:
        return await message.reply(f"You haven't added the items yet.\n{USAGE}")

    items_obj = []
    for item in items:
        item_obj = Item.get(item.item_id)
        item_obj.keepa = item
        items_obj.append(item_obj)

    # noinspection PyProtectedMember
    unparsed_item_ids = [i.id_ for i in items_obj if not i._parsed]  # noqa: SLF001
    if unparsed_item_ids:
        message = await message.reply(f"One moment. Parsing {len(unparsed_item_ids)} items", disable_notification=True)
        Item.parse_multiple(*unparsed_item_ids, parse_subitems=False)
        await message.delete()

    msgs = []
    msg = "Your Watched Items:"
    for item_obj in items_obj:
        if not hasattr(item_obj, "price"):
            await message.answer(
                f"Nonexistent item {html.link(item_obj.keepa.item_id, item_obj.keepa.url)}",
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML,
            )
            continue

        price_diff = item_obj.keepa.wanted_price - item_obj.price
        price_diff_str = f"({price_diff})"
        msg_ = f"""
{html.link(item_obj.id_, item_obj.href)} {html.link(item_obj.title, item_obj.href)}
Cached Price: {item_obj.price}
Wanted Price: {item_obj.keepa.wanted_price} {price_diff_str}
Cached Availability: {tools.sell_status_str(item_obj.sell_status)}
"""
        msg_tryout = msg + msg_
        if len(msg_tryout) >= constants.MAX_MESSAGE_LENGTH:
            msgs.append(msg)
            msg = ""
        msg += msg_
    msgs.append(msg)
    for msg in msgs:
        await message.answer(msg, disable_web_page_preview=True, parse_mode=ParseMode.HTML)
    return None


@router.message(Command("test"))
async def test_(message: Message):
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text="Page", url="https://google.com")
    remove_watch_callback_data = RemoveItemCallback(item_id=123456).pack()
    builder.button(text="item", callback_data=remove_watch_callback_data)
    await message.answer(
        text="test",
        parse_mode=ParseMode.HTML,
        allow_sending_without_reply=True,
        reply_markup=builder.as_markup(),
    )
