import os

from global_logger import Log
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

log = Log.get_logger()
if os.getenv("VERBOSE") == "True":
    log.verbose = True

MAX_MESSAGE_LENGTH = 4096

INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

TELEGRAM_BOT_API_TOKEN = os.getenv("TELEGRAM_BOT_API_TOKEN")
DB_URL = os.getenv("DB_URL")

TELEGRAM_ANNOUNCE_CHAT = os.getenv("TELEGRAM_ANNOUNCE_CHAT")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
SLACK_USER_MENTIONS = os.getenv("SLACK_USER_MENTIONS", "")
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")
TEAMS_USER_MENTIONS = os.getenv("TEAMS_USER_MENTIONS", "")

LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "3600"))

TZ_ENV = os.getenv("TZ", "Europe/London")

TZ = ZoneInfo(TZ_ENV)
