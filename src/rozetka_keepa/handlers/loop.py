from __future__ import annotations

import asyncio

import pendulum
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.text_decorations import HtmlDecoration, MarkdownDecoration
from global_logger import Log
from rozetka.entities.item import Item

from ..db import DBController  # noqa: TID252
from ..models.callbacks import RemoveItemCallback  # noqa: TID252
from .. import constants  # noqa: TID252


LOG = Log.get_logger()


dbc = DBController.instantiate()

html = HtmlDecoration()
md = MarkdownDecoration()

router = Router()

background_tasks = set()


async def check(bot: Bot, dispatcher: Dispatcher, bots: list, router: Dispatcher):  # noqa: ARG001
    LOG.debug("Checker")
    keepas = dbc.get_keepas()
    if keepas:
        item_ids = [i.item_id for i in keepas]
        Item.parse_multiple(*item_ids, parse_subitems=False)
        for keepa in keepas:
            pause_until = pendulum.instance(keepa.pause_until, tz=pendulum.local_timezone())
            skip = pause_until > pendulum.now(tz=pendulum.local_timezone())
            if skip:
                continue

            item = keepa.item
            available = (status := getattr(item, "sell_status", "available")) not in ("unavailable",)
            if not available:
                LOG.debug(f"Skipping {keepa} for {item}: Status: {status}")
                continue

            price_current = item.price
            price_wanted = keepa.wanted_price
            if price_current is not None and price_current <= price_wanted:
                user = dbc.get_user(id=keepa.user_id)
                if not user:
                    LOG.warning(f"No User found for watched {keepa}")
                    continue

                user = user[0]
                msg = f"""
    Price trigger for {html.link(item.id_, item.href)}
    {item.title}
    Wanted: {price_wanted}
    Current: {price_current}
    """
                builder = InlineKeyboardBuilder()
                builder.button(text="Page", url=item.href)
                remove_watch_callback_data = RemoveItemCallback(item_id=item.id_).pack()
                builder.button(text="Remove Watch", callback_data=remove_watch_callback_data)
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=item.image_main,
                    caption=msg,
                    parse_mode=ParseMode.HTML,
                    allow_sending_without_reply=True,
                    reply_markup=builder.as_markup(),
                )
                keepa.pause()
            elif price_current is not None and price_current > price_wanted:
                keepa.reset_pause()
            elif price_current is None:
                LOG.warning(f"No record found on {keepa}")
                continue

    dbc.commit()


async def checker_loop(bot: Bot, dispatcher: Dispatcher, bots: list, router_: Dispatcher):
    while True:
        await check(bot, dispatcher, bots, router_)
        await asyncio.sleep(constants.LOOP_INTERVAL)


async def on_startup(bot: Bot, dispatcher: Dispatcher, bots: list, router_: Dispatcher):
    task = asyncio.create_task(checker_loop(bot, dispatcher, bots, router_))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


router.startup.register(on_startup)
