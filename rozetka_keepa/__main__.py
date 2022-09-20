from aiogram import executor
from global_logger import Log

from rozetka_keepa import constants
from rozetka_keepa.telegram import dp, checker_loop

LOG = Log.get_logger()

if __name__ == '__main__':
    assert constants.INFLUXDB_URL and constants.INFLUXDB_TOKEN and constants.INFLUXDB_ORG \
           and constants.INFLUXDB_BUCKET, "Please fill all INFLUXDB variables"

    assert constants.TELEGRAM_BOT_API_TOKEN, "Please fill Telegram variables"
    assert constants.DB_URL, "Please fill Database variables"

    executor.start_polling(dp, skip_updates=True, on_startup=checker_loop)  # todo: notify on crash
