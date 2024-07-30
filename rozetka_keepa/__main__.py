import asyncio

from global_logger import Log
from knockknock import discord_sender, slack_sender, teams_sender, telegram_sender

from rozetka_keepa import constants
from rozetka_keepa.telegram import main

LOG = Log.get_logger()


def _main():
    return asyncio.run(main())


if __name__ == "__main__":
    assert constants.INFLUXDB_URL, "Please fill INFLUXDB_URL variable"
    assert constants.INFLUXDB_TOKEN, "Please fill all INFLUXDB_TOKEN variable"
    assert constants.INFLUXDB_ORG, "Please fill all INFLUXDB_ORG variable"
    assert constants.INFLUXDB_BUCKET, "Please fill all INFLUXDB_BUCKET variable"

    assert constants.TELEGRAM_BOT_API_TOKEN, "Please fill TELEGRAM_BOT_API_TOKEN variable"
    assert constants.DB_URL, "Please fill DB_URL variable"

    fnc = _main  # https://github.com/huggingface/knockknock
    if tg_chat := constants.TELEGRAM_ANNOUNCE_CHAT:
        fnc = telegram_sender(token=constants.TELEGRAM_BOT_API_TOKEN, chat_id=int(tg_chat))(fnc)

    if discord_webhook := constants.DISCORD_WEBHOOK_URL:
        fnc = discord_sender(discord_webhook)(fnc)

    if (slack_webhook := constants.SLACK_WEBHOOK_URL) and (slack_channel := constants.SLACK_CHANNEL):
        if slack_user_mentions := constants.SLACK_USER_MENTIONS:
            slack_user_mentions = slack_user_mentions.split()
        fnc = slack_sender(slack_webhook, slack_channel, slack_user_mentions)(fnc)

    if teams_webhook := constants.TEAMS_WEBHOOK_URL:
        if teams_user_mentions := constants.TEAMS_USER_MENTIONS:
            teams_user_mentions = teams_user_mentions.split()
        fnc = teams_sender(teams_webhook, teams_user_mentions)(fnc)

    fnc()
