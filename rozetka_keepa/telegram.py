import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats
from aiogram.utils.text_decorations import HtmlDecoration, MarkdownDecoration
from rozetka_keepa.handlers import commands, loop
from rozetka_keepa import constants

from global_logger import Log

LOG = Log.get_logger()

html = HtmlDecoration()
md = MarkdownDecoration()


async def set_commands(bot: Bot):
    data = [
        (
            [
                BotCommand(command="start", description="start"),
                BotCommand(command="items", description="items list"),
                BotCommand(command="list", description="items list"),
                BotCommand(command="remove", description="remove item"),
                BotCommand(command="item", description="get/add item"),
                BotCommand(command="deleteme", description="unregister"),
                # BotCommand(command="test", description="test"),
            ],
            BotCommandScopeAllPrivateChats(),
            None
        )
    ]
    for commands_list, commands_scope, language in data:
        await bot.set_my_commands(commands=commands_list, scope=commands_scope, language_code=language)


async def main() -> None:
    bot = Bot(token=constants.TELEGRAM_BOT_API_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(loop.router)
    dp.include_router(commands.router)
    dp.message.filter(F.chat.type == "private")
    await set_commands(bot)
    await dp.start_polling(bot)  # , allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    asyncio.run(main())
