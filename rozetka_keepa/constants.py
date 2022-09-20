import os

from global_logger import Log

log = Log.get_logger()
if os.getenv('VERBOSE') == 'True':
    log.verbose = True

INFLUXDB_URL = os.getenv('INFLUXDB_URL')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')

TELEGRAM_BOT_API_TOKEN = os.getenv('TELEGRAM_BOT_API_TOKEN')
DB_URL = os.getenv('DB_URL')
