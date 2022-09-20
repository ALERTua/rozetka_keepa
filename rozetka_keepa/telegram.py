import asyncio
import re
from copy import copy

import pendulum
from aiogram import Bot, Dispatcher, executor, types
from global_logger import Log

from rozetka_keepa import constants, tools
from rozetka_keepa.db import DBController
from rozetka_keepa.influxdb import InfluxDBController

LOG = Log.get_logger()

bot = Bot(token=constants.TELEGRAM_BOT_API_TOKEN)
dp = Dispatcher(bot)

ITEM_CMD = '/item'
USAGE = f"Usage: {ITEM_CMD} ID PRICE"
REGISTER = '/start'
REGISTER_USAGE = f'Use {REGISTER} to register'

dbc = DBController.instantiate()


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


@dp.message_handler(commands=['remove'])
async def remove_item(message: types.Message):  # /remove 123
    cmd = '/remove'
    obj = message.text.replace(f'{cmd} ', '')  # 123
    if not re.match(r'\d+', obj):
        await message.reply(f"Usage: {cmd} ID")
        return

    item_id = int(obj)
    telegram_id = message.from_user.id
    kwargs = dict(telegram_id=telegram_id)
    exists = dbc.get_user(**kwargs)
    if not exists:
        await message.reply(f"Your user does not exist.\n{REGISTER_USAGE}")
        return

    user = exists[0]

    existing = dbc.get_user_item_id(user, item_id=item_id)
    if existing:
        item = existing[0]
        await message.reply(f"Item {item} removed from watched")
        dbc.remove_item(item)
        return
    else:
        await message.reply(f"You didn't add an item ID {item_id}\n{USAGE}")
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

    items_str = '\n'.join([str(i) for i in items])
    await message.reply(f"Your Watched Items:\n{items_str}")  # todo: good repr with urls


@dp.async_task
async def checker_loop(*args, **kwargs):
    while True:
        keepas = dbc.get_keepas()
        if keepas:
            item_ids = [i.item_id for i in keepas]
            prices_current = await InfluxDBController.get_prices_async(item_ids)
            for keepa in keepas:
                pause_until = pendulum.instance(keepa.pause_until)
                if pause_until > pendulum.now():
                    continue

                price_current = prices_current.get(keepa.item_id)
                price_wanted = keepa.wanted_price
                if price_current is not None and price_current <= price_wanted:  # todo: check price is recent
                    user = dbc.get_user(id=keepa.user_id)
                    if not user:
                        LOG.warning(f"No User found for watched {keepa}")
                        continue

                    user = user[0]
                    msg = f'Price trigger for {keepa} {keepa.url}\nWanted: {price_wanted}.\nCurrent: {price_current}'
                    await bot.send_message(chat_id=user.telegram_id, text=msg)  # todo: inline, image, item title
                    keepa.pause()
                elif price_current is not None and price_current > price_wanted:
                    keepa.reset_pause()
                elif price_current is None:
                    LOG.warning(f"No InfluxDB record found on {keepa}")
                    continue

        dbc.commit()
        await asyncio.sleep(pendulum.Duration(hours=1).in_seconds())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=checker_loop)
