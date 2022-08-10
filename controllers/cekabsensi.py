from datetime import datetime

from pytz import timezone

import models.groupware as groupware
import models.bot as bot
import models.user as user

def action_cekabsensi(telegram_item):
    """ action for /cekabsensi command """
    timezone_jkt = timezone('Asia/Jakarta')
    # now = datetime.now(timezone_jkt)
    now = datetime.now()
    attendance_list = user.get_users_attendance(now.strftime('%Y-%m-%d'))
    print(attendance_list)
    attendance_list_clean = []

    divisi = None
    input_data = telegram_item['message']['text'].strip().split(' ') \
                 if 'text' in telegram_item['message'] \
                 else []
    if len(input_data) > 1 :
        divisi = input_data[1].lower()
        attendance_list = [
            row
            for row
            in attendance_list
            if row[4][:2].lower() == divisi[:2]
        ]

    row_num = 1
    for row in sorted(attendance_list):
        if not row[3]:
            attendance_list_clean.append("{}. {} ({})".format(
                    row_num,
                    row[1],
                    row[2]
                )
            )

            row_num += 1

    if (len(attendance_list_clean) > 1):
        msg_lines = [ """Halo DigiTeam! Presensi kehadiran dan laporan harianmu adalah tanggung jawab sekaligus syarat untuk administrasi penggajian.

Berikut nama-nama yang belum Check In hari ini (per {} jam {}).
    """.format(
            now.strftime('%d-%m-%Y'),
            now.strftime('%H:%M'),
        )
        ] + attendance_list_clean + [
        """
Yuk, maksimalkan aplikasi DigiTeam untuk mudahkan pekerjaanmu!

Semangat dan sehat selalu! Hatur nuhun!
        """
        ]
    else:
        msg_lines = [ """Yeaaay, presensi hari ini ({}) sudah lengkap! {} orang sudah mengisi presensi hari ini.

Terima kasih banyak buat dedikasi dan kontribusi Digiteam semua untuk mengakselerasi digitalisasi di Jawa Barat. Tetap jaga iman, imun & aman, ya, teman-teman  🥳🥳🥳
    """.format(
            now.strftime('%d-%m-%Y'),
            len(attendance_list)
        ) ]

    if divisi is None:
        msg_lines.insert(0, "#INFOABSENSI")
    else:
        msg_lines.insert(0, f"#INFOABSENSI DIVISI {divisi.upper()}")

    return bot.reply_message_paginated(telegram_item, msg_lines)

