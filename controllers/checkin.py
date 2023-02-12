from datetime import datetime, date, time
from pytz import timezone
from dotenv import load_dotenv
from pathlib import Path
import os, requests, json
import models.bot as bot
import models.groupware as groupware
import models.user as user
env_path = Path(__file__).parent.parent /  '.env'
load_dotenv(dotenv_path=env_path)

ROOT_API_URL = os.getenv('ROOT_API_URL')
CHECKIN_URL = ROOT_API_URL+'/attendance/checkin/'
PREDEFINED_CUSTOM_WAKTU = '07:30:00'

def action_checkin(item, peserta=None):
    """ action for /checkin command """
    # parse input
    if 'caption' in item['message']:
        input_text = item['message']['caption']
    elif 'text' in item['message']:
        input_text = item['message']['text']

    lines = input_text.split("\n")
    first_params = lines[0]
    first_params = first_params[first_params.find(' ')+1 :] # start from after first ' '

    current_time = datetime.now(timezone('Asia/Jakarta'))

    # default values
    username = '@' + item['message']['from']['username']
    location = first_params.upper()
    checkin_time = current_time
    tanggal   = checkin_time.strftime('%Y-%m-%d')
    waktu = checkin_time.strftime('%H:%M')

    #batas waktu checkin
    awal_waktu_checkin = "05:30"
    batas_waktu_checkin = "07:30"

    if waktu < awal_waktu_checkin :
        msg = "Checkin bisa dilakukan setelah 05:30"
        return bot.reply_message(item, msg)
    
    if waktu > batas_waktu_checkin :
        msg = "Checkin gagal | waktu melebihi 07:30, silahkan checkin menggunakan https://groupware.digitalservice.id/"
        return bot.reply_message(item, msg)

    # custom values
    first_params = first_params.split('|') # split with '|'

    if len(first_params) >= 2 :
        username = first_params[0].strip()
        location = first_params[1].strip().upper()

    if len(first_params) == 3 :
        tanggal = first_params[2].strip()

        tanggal = date.fromisoformat(tanggal)
        waktu = time.fromisoformat(PREDEFINED_CUSTOM_WAKTU)
        checkin_time = datetime.combine(tanggal, waktu, timezone('Asia/Jakarta'))

    checkin_time_utc = checkin_time.astimezone(timezone('UTC'))
    checkinDateTimeFormat = checkin_time_utc.strftime('%Y-%m-%dT%H:%M:%I.000Z')

    locationAvailable = ['WFH','WFO','PERJADIN']

    if location in locationAvailable:

        data = {
            'date': checkinDateTimeFormat,
            'location': location,
            'message': "HADIR",
            'note': "",
            'mood': "neutral"
        }

        getToken = user.get_user_token(username)

        req = requests.post(
            url=CHECKIN_URL,
            headers={
                'Authorization': 'Bearer ' + getToken,
            },
            data=data
        )

        msg = "%s | HADIR %s Pukul %s %s %s" % (username, tanggal , waktu, bot.EMOJI_SUCCESS, location)
        responseMessage = json.loads(req.text)

        if req.status_code >= 300:
            e = ValueError("%s | Checkin Gagal | %s %s " % (username, responseMessage["message"], bot.EMOJI_FAILED))
            return bot.process_error(item, e)
        else:
            return bot.reply_message(item, msg)

    else:
        msg = "Checkin gagal | Jenis kehadiran anda tidak sesuai"
        return bot.reply_message(item, msg)
