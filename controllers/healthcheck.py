import json
import traceback
from fastapi import HTTPException

import models.db as db
import models.bot as bot
import models.groupware as groupware

def run():
    """ get healtcheck status of Digiteam Telegram Bot """
    try:
        db_status = db.is_db_connected()
        groupware_api_status = groupware.is_groupware_api_reachable()
        telegram_status = bot.get_webhook_status()
        if isinstance(telegram_status['result'], list):
            telegram_status['result']['url'] = '--REDACTED--' # censor actual URL
            telegram_status['result']['ip_address'] = '--REDACTED--' # censor actual ip address

        return {
            'webserver': {
                'ok': True,
                'message': None,
            },
            'database': {
                'ok': db_status[0],
                'message': db_status[1],
            },
            'groupware_api': {
                'ok': groupware_api_status[0],
                'message': groupware_api_status[1],
            },
            'telegram': {
                'ok': telegram_status['ok'],
                'message': json.dumps(telegram_status['result']),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=json.dumps({
            'err_msg': str(e),
            'traceback': traceback.format_exc(),
        }))

