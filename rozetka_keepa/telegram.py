import asyncio
import re
from copy import copy

import pendulum
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.markdown import escape_md
from aiogram.utils.parts import MAX_MESSAGE_LENGTH
from global_logger import Log
from rozetka.entities.item import Item

from rozetka_keepa import constants, tools
from rozetka_keepa.db import DBController

LOG = Log.get_logger()

bot = Bot(token=constants.TELEGRAM_BOT_API_TOKEN)
dp = Dispatcher(bot)

ITEM_CMD = '/item'
USAGE = f"Usage: {ITEM_CMD} ID PRICE"
REGISTER = '/start'
REGISTER_USAGE = f'Use {REGISTER} to register'

dbc = DBController.instantiate()


def sell_status_str(sell_status):
    if sell_status == 'unavailable':
        return f'❌'
    elif sell_status == 'available':
        return f'✅'
    else:
        return sell_status


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    telegram_id = message.from_user.id
    kwargs = dict(telegram_id=telegram_id)
    exists = dbc.get_user(**kwargs)
    if exists:
        await message.reply("You are already registered.")
        return

    user = dbc.create_user(**kwargs)
    dbc.commit()
    await message.reply("You are are now registered.")


@dp.message_handler(commands=['deleteme'])
async def deleteme(message: types.Message):
    telegram_id = message.from_user.id
    kwargs = dict(telegram_id=telegram_id)
    exists = dbc.get_user(**kwargs)
    if not exists:
        await message.reply("Your user does not exist.")
        return

    user = exists[0]
    dbc.delete_user(user)
    await message.reply("Your user is removed.")


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('/remove'))
@dp.message_handler(commands=['remove'])
async def remove_item(message: types.Message | types.CallbackQuery):  # /remove 123
    cmd = '/remove'
    text = getattr(message, 'text') or getattr(message, 'data')
    message_obj = getattr(message, 'message', message)
    obj = text.replace(f'{cmd} ', '')  # 123
    if not re.match(r'\d+', obj):
        await message.reply(f"Usage: {cmd} ID")
        return

    item_id = int(obj)
    telegram_id = message.from_user.id
    chat_id = message_obj.chat.id
    kwargs = dict(telegram_id=telegram_id)
    exists = dbc.get_user(**kwargs)
    if not exists:
        await bot.send_message(chat_id=chat_id, text=f"Your user does not exist.\n{REGISTER_USAGE}")
        return

    user = exists[0]

    existing = dbc.get_user_item_id(user, item_id=item_id)
    if existing:
        item = existing[0]  #
        dbc.remove_item(item)
        await bot.send_message(chat_id=chat_id, text=f"Item {item} removed from watched list")
        return
    else:
        await bot.send_message(chat_id=chat_id, text=f"You didn't add an item ID {item_id}\n{USAGE}")
        return


@dp.message_handler(commands=['item'])
async def add_edit_item(message: types.Message):
    obj = message.text.replace(f'{ITEM_CMD} ', '')  # /item 123 12.99
    obj_split = obj.split(' ')  # ['123', '12.99']
    if len(obj_split) == 1:  # ['123']
        item_id = obj_split[0]
        price_str = None
    elif not len(obj_split) == 2:
        return await message.reply(USAGE)
    else:
        item_id, price_str = obj_split  # '123' '12.99'

    if not re.match(r'\d+', item_id):
        return await message.reply(USAGE)

    item_id = int(item_id)

    telegram_id = message.from_user.id
    kwargs = dict(telegram_id=telegram_id)
    exists = dbc.get_user(**kwargs)
    if not exists:
        return await message.reply(f"Your user does not exist.\n{REGISTER_USAGE}")

    user = exists[0]

    existing = None
    if price_str is None:
        existing = dbc.get_user_item_id(user, item_id=item_id)
        if existing:
            item = existing[0]
            await message.reply(f"Item {item.id} is watched for price {item.wanted_price}. It was added @ {item.added}")
            return
        else:
            return await message.reply(f"You didn't add an item ID {item_id}\n{USAGE}")

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


@dp.message_handler(commands=['list', 'items'])
async def list_(message: types.Message):
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
    unparsed_item_ids = [i.id_ for i in items_obj if not i._parsed]
    if unparsed_item_ids:
        message = await message.reply(f"One moment. Parsing {len(unparsed_item_ids)} items")
        Item.parse_multiple(*unparsed_item_ids, parse_subitems=False)
        await message.delete()

    msgs = []
    msg = f"Your Watched Items:"
    for item_obj in items_obj:
        price_diff = item_obj.keepa.wanted_price - item_obj.price
        price_diff_str = f'({price_diff})'
        msg_ = f"""        
[{item_obj.id_}]({item_obj.href}) {escape_md(item_obj.title)}
Cached Price: {escape_md(item_obj.price)}
Wanted Price: {escape_md(item_obj.keepa.wanted_price)} {escape_md(price_diff_str)}
Cached Availability: {escape_md(sell_status_str(item_obj.sell_status))}
"""
        msg_tryout = msg + msg_
        if len(msg_tryout) >= MAX_MESSAGE_LENGTH:
            msgs.append(msg)
            msg = ""
        msg += msg_
    msgs.append(msg)
    for msg in msgs:
        await message.reply(msg, disable_web_page_preview=True, parse_mode=types.ParseMode.MARKDOWN_V2, reply=False)


@dp.async_task
async def checker_loop(*args, **kwargs):
    while True:
        keepas = dbc.get_keepas()
        if keepas:
            item_ids = [i.item_id for i in keepas]
            Item.parse_multiple(*item_ids, parse_subitems=False)
            # prices_influx = await InfluxDBController.get_prices_async(item_ids)
            for keepa in keepas:
                pause_until = pendulum.instance(keepa.pause_until, tz=pendulum.local_timezone())
                if pause_until > pendulum.now(tz=pendulum.local_timezone()):
                    continue

                item = keepa.item
                # price_current = prices_influx.get(keepa.item_id)
                price_current = item.price
                price_wanted = keepa.wanted_price
                if price_current is not None and price_current <= price_wanted:
                    user = dbc.get_user(id=keepa.user_id)
                    if not user:
                        LOG.warning(f"No User found for watched {keepa}")
                        continue

                    user = user[0]
                    msg = f"""
Price trigger for [{item.id_}]({item.href})
{escape_md(item.title)}
Wanted: {escape_md(price_wanted)}
Current: {escape_md(price_current)}
"""
                    # https://surik00.gitbooks.io/aiogram-lessons/content/chapter5.html
                    page_url = InlineKeyboardButton('Page', url=item.href)
                    remove_item_btn = InlineKeyboardButton('Remove Watch', callback_data=f'/remove {keepa.item_id}')
                    inline = InlineKeyboardMarkup(resize_keyboard=True).row(page_url, remove_item_btn)
                    await bot.send_photo(chat_id=user.telegram_id, photo=item.image_main, caption=msg,
                                         parse_mode=types.ParseMode.MARKDOWN_V2, allow_sending_without_reply=True,
                                         reply_markup=inline)
                    keepa.pause()
                elif price_current is not None and price_current > price_wanted:
                    keepa.reset_pause()
                elif price_current is None:
                    LOG.warning(f"No record found on {keepa}")
                    continue

        dbc.commit()
        await asyncio.sleep(pendulum.Duration(hours=1).in_seconds())


# @dp.callback_query_handler(lambda callback_query: True)
# async def process_callback_kb1btn1(callback_query: types.CallbackQuery):
#     pass


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=checker_loop)
