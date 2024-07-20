#!/usr/bin/env python3

import time
from datetime import datetime
from telebot import TeleBot
from pyTelegramBotCAPTCHA import CaptchaManager, CaptchaOptions

from pyTelegramBotCAPTCHA.telebot_captcha import languages
languages['en']['text'] = 'Tervetuloa, #USER!\n\nWe want to check that you are not a bot. Which five numbers do you see?\n\nHaluamme tarkistaa, että et ole botti. Mitkä viisi numeroa näet kuvassa?\n\n🔁: new captcha / uusi captcha\n⬅️: erase / askelpalautin\n✅: submit / lähetä\n'

MAX_ATTEMPTS = 3
with open('bot_token.txt', 'r') as botTokenFile:
    BOT_TOKEN = botTokenFile.read().strip()

bot = TeleBot(BOT_TOKEN)
captcha_manager = CaptchaManager(
    bot_id=bot.get_me().id,
    default_options=CaptchaOptions(
        generator="default",
        timeout=180,                # 5 minutes to solve captcha
        code_length=5,              # captcha length
        max_user_reloads=3,         # how many times user can reload captcha manually
        max_attempts=MAX_ATTEMPTS,  # how many attempts user can perform
        only_digits=True,
    ),
)


ts = lambda: datetime.now().strftime('[%Y-%m-%d %H:%M:%S.%f]')
log = lambda text: print(f'{ts()} {text}', flush=True)


def is_enabled_for_group(chat_id: int) -> bool:
    return True  # TODO: restrict by chat ids


@bot.message_handler(content_types=["new_chat_members"])
def new_member(message):
    if not is_enabled_for_group(message.chat.id):
        return
    for user in message.new_chat_members:
        captcha_manager.restrict_chat_member(bot, message.chat.id, user.id)
        captcha_manager.send_new_captcha(bot, message.chat, user)
        log(f'New user detected: chat_id={message.chat.id}, user_id: {user.id}')


@bot.callback_query_handler(func=lambda callback: True)
def on_callback(callback):
    if not is_enabled_for_group(callback.message.chat.id):
        return
    captcha_manager.update_captcha(bot, callback)


@captcha_manager.on_captcha_correct
def on_correct(captcha):
    if not is_enabled_for_group(captcha.chat.id):
        return
    captcha_manager.unrestrict_chat_member(bot, captcha.chat.id, captcha.user.id)
    captcha_manager.delete_captcha(bot, captcha)
    log(f'User solved captcha: chat_id={captcha.chat.id}, user_id: {captcha.user.id}')


def kick_user_without_ban(chat_id, user_id):
    bot.unban_chat_member(chat_id, user_id, only_if_banned=False)


@captcha_manager.on_captcha_not_correct
def on_not_correct(captcha):
    if not is_enabled_for_group(captcha.chat.id):
        return
    if captcha.previous_tries < MAX_ATTEMPTS:
        captcha_manager.refresh_captcha(bot, captcha)
    else:
        kick_user_without_ban(captcha.chat.id, captcha.user.id)
        captcha_manager.delete_captcha(bot, captcha)
        log(f'User failed ALL attempts to solve captcha and was kicked: previous_tries={captcha.previous_tries}, chat_id={captcha.chat.id}, user_id: {captcha.user.id}')


@captcha_manager.on_captcha_timeout
def on_timeout(captcha):
    if not is_enabled_for_group(captcha.chat.id):
        return
    kick_user_without_ban(captcha.chat.id, captcha.user.id)
    captcha_manager.delete_captcha(bot, captcha)
    log(f'User failed to solve captcha in time and was kicked: chat_id={captcha.chat.id}, user_id: {captcha.user.id}')


def run_bot():
    while True:
        try:
            log(f'Bot starts polling')
            bot.polling(non_stop=True)
        except KeyboardInterrupt:
            log(f'Stopping on keyboard interrupt')
            bot.stop_polling()
            break
        except Exception as e:
            log(f'Bot polling failed: {e}, restarting in 1 second')
            time.sleep(1)

if __name__ == '__main__':
    run_bot()
    log(f'Bot has stopped')
