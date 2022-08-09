import models.user as user
import models.bot as bot

def action_setalias(telegram_item):
    """ action for /setalias command """
    # parse input
    if 'text' in telegram_item['message']:
        input_text = telegram_item['message']['text']

    input_text = input_text.split(' ', maxsplit=1)[1] # start from after first ' '
    val = input_text.split('|')
    res, msg = user.set_alias(val[0].strip(), val[1].strip() )

    print('hasil setalias:', res, msg)

    bot.reply_message(telegram_item, msg, is_direct_reply=True)

    return None if not res else res

def action_listalias(telegram_item):
    msg_list = [
        'Daftar alias user di JDS:',
        '(format: @username_telegram = username_digiteam)',
    ] + [
        '- {} = {}'.format(username_telegram, username_digiteam)
        for username_telegram, username_digiteam in
        user.ALIAS.items()
    ]

    return bot.reply_message_paginated(telegram_item, msg_list, is_direct_reply=True)

def action_removealias(telegram_item):
    """ action for /removealias command """
    # parse input
    if 'text' in telegram_item['message']:
        input_text = telegram_item['message']['text']

    telegram_username = input_text.split(' ', maxsplit=1)[1] # start from after first ' '

    print(telegram_username)
    res, msg = user.remove_alias(telegram_username.strip() )

    bot.reply_message(telegram_item, msg, is_direct_reply=True)

    return None if not res else res
