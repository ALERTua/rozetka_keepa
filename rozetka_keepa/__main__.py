import asyncio

from global_logger import Log

from rozetka_keepa import constants
from rozetka_keepa.telegram import main

LOG = Log.get_logger()


def _main():
    LOG.trace()
    return asyncio.run(main())


if __name__ == "__main__":
    assert constants.INFLUXDB_URL, "Please fill INFLUXDB_URL variable"
    assert constants.INFLUXDB_TOKEN, "Please fill all INFLUXDB_TOKEN variable"
    assert constants.INFLUXDB_ORG, "Please fill all INFLUXDB_ORG variable"
    assert constants.INFLUXDB_BUCKET, "Please fill all INFLUXDB_BUCKET variable"

    assert constants.TELEGRAM_BOT_API_TOKEN, "Please fill TELEGRAM_BOT_API_TOKEN variable"
    assert constants.DB_URL, "Please fill DB_URL variable"

    _main()
