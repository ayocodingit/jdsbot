"""
This module handle all function regarding bot actions including parsing telegram
update data, sending telegram message, handling command and input, etc
"""
import os, json, time, traceback

import requests
from dotenv import load_dotenv
load_dotenv()

import models.groupware as groupware
import models.bot as bot
import models.user as user
import models.db as db
import models.chat_history as chat_history
import controllers.checkin as checkin
import controllers.checkout as checkout
import controllers.lapor as lapor
import controllers.tambah as tambah
import controllers.setalias as setalias
import controllers.cekabsensi as cekabsensi
import controllers.ulangtahun as ulangtahun
from controllers.help import action_help

processed=[]
START_TIME = time.time()
LIST_CUTOFF_NUM = os.getenv('LIST_CUTOFF_NUM', 90)

def setup():
    """ iniate bot_controller """
    user.load_user_data()
    auth_token = user.get_user_token(os.getenv('TEST_USER'))
    groupware.load_project_list(auth_token)

    print('PROJECT_LIST:', groupware.PROJECT_LIST)
    print('user.ALIAS:', user.ALIAS)

def action_about(telegram_item):
    """ action for /about command """
    # banyak karakter yang perlu di escape agar lolos parsing markdown di telegram. ref: https://core.telegram.org/bots/api#markdownv2-style
    msg = """Halo\! Aku adalah {}\. Aku ditugaskan untuk membantu melakukan rekap evidence gambar, nama proyek, dan nama task laporan harian otomatis ke aplikasi digiteam groupware\. Silahkan ketik di kolom chat `/help` untuk melihat command\-command yang bisa aku lakukan\! """.format(bot.BOT_NICKNAME)
    return bot.reply_message(telegram_item, msg, is_markdown=True)

def action_whatsnew(telegram_item):
    """ action for /whatsnew command """
    # banyak karakter yang perlu di escape agar lolos parsing markdown di telegram. ref: https://core.telegram.org/bots/api#markdownv2-style
    msg = """\#UPDATERILIS
Per tanggal 26 November 2021, ada beberapa perubahan:

\- Perbaikan command `/setalias`\. Untuk mencegah konflik dari alias yang sama, sekarang akan muncul pesan error jika kamu mencoba mendaftarkan user alias yang sudah ada sebelumnya\.
\- Untuk command `/checkin` dan `/checkout` sekarang secara default akan menggunakan akun user yang mengirimkan command tersebut, sehingga kamu tidak perlu menyebutkan user kamu sendiri\.
"""
    return bot.reply_message(telegram_item, msg, is_markdown=True)

def action_listproject(telegram_item):
    """ action for /listproject command """
    # banyak karakter yang perlu di escape agar lolos parsing markdown di telegram. ref: https://core.telegram.org/bots/api#markdownv2-style
    msg = "List project\-project di aplikasi DigiTeam saat ini:\n"

    key_list = sorted(list(groupware.PROJECT_LIST.keys()))

    for (index, item) in enumerate(key_list):
        msg += "\- `{}`\n".format(groupware.PROJECT_LIST[item]['originalName'])

        # kalau isi list terlalu banyak, potong sesuai konstanta LIST_CUTOFF_NUM
        if ((index+1) % LIST_CUTOFF_NUM == 0):
            bot.reply_message(telegram_item, msg, is_markdown=True)
            msg = ''

    # kalau masih ada yang blm ter-send
    if len(msg) > 0:
        bot.reply_message(telegram_item, msg, is_markdown=True)

    return True

def action_reload(telegram_item):
    """ action for /reload_data command """
    if db.CONNECTION is not None:
        db.CONNECTION.close()

    try:
        setup()
    except Exception as e:
        print(e)
        print(traceback.print_exc())
        bot.process_error(telegram_item, e)
        return None

    return bot.reply_message(telegram_item, 'reload success')

def action_ngobrol(telegram_item):
    """ chat sebagai bot telegram """
    pecah2 = telegram_item['message']['text'].split(' ', maxsplit=2)

    return bot.run_command('/sendMessage', {
        'chat_id': pecah2[1],
        'text': pecah2[2],
    })

def process_telegram_input(item):
    """ process a single telegram update item
    Return
    ------
    mixed:
        None is ignoring message
    """
    if 'message' not in item :
        print('update contain no message, ignoring...')
        return None

    print('receiving input :', item['message'])
    print('time: {} message_id: {}'.format(
        item['message']['date'],
        item['message']['message_id']
    ))

    if item['message']['date'] < START_TIME :
        print('old message, ignoring...')
        return None

    if 'caption' in item['message']:
        input_text = item['message']['caption']
    elif 'text' in item['message']:
        input_text = item['message']['text']
    else:
        print('message contain no text, ignoring...')
        return None

    print('receiving input :', input_text)

    available_commands = {
        '/lapor' : lapor.action_lapor,
        '/tambah' : tambah.action_tambah,
        '/start' : action_about,
        '/about' : action_about,
        '/help' : action_help,
        '/whatsnew' : action_whatsnew,
        '/setalias' : setalias.action_setalias,
        '/listproject': action_listproject,
        '/reload_data': action_reload,
        '/cekabsensi': cekabsensi.action_cekabsensi,
        '/ngobrol' : action_ngobrol,
        '/checkin' : checkin.action_checkin,
        '/checkout' : checkout.action_checkout,
        '/ulangtahun' : ulangtahun.action,
    }
    command = input_text.split(' ', maxsplit=1)[0].strip()
    if command[0] != '/':
        print("First word ({}) is not a command (beginning with '/'). ignoring...".format(command))
        return None

    sub_command = command.split('@')
    if len(sub_command) > 1:
        if sub_command[1].upper() != bot.BOT_USERNAME:
            print('command not for this bot, ignoring...')
            return None
        command = sub_command[0]

    command = command.lower()
    if command not in available_commands :
        bot.process_error(item, "Unknown command '{}'".format(command))
        return None

    try:
        res = available_commands[command](item)
    except Exception as e:
        bot.process_error(item, e)
        return None

    return res

def loop_updates(updates):
    """ loop through all update from telegram's getUpdates endpoint """
    global processed

    for item in updates:
        if 'message' in item and 'text' in item['message'] \
        and item['message']['message_id'] not in processed \
        and item['message']['date'] < START_TIME \
        :
            processed.append(item['message']['message_id'])
            process_telegram_input(item)

def is_today_holiday():
    """ simple wrapper for groupware.check_date_is_holiday() """
    auth_token = user.get_user_token(os.getenv('TEST_USER'))
    return groupware.check_date_is_holiday(auth_token)

if __name__ == '__main__':
    import sys
    sleep_interval = 3 if len(sys.argv) < 2 else sys.argv[1]

    while True:
        res = bot.run_command('/getUpdates')
        loop_updates(res['result'])
        time.sleep(3)
