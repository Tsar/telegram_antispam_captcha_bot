#!/usr/bin/env python3

from telebot import TeleBot
from pyTelegramBotCAPTCHA import CaptchaManager, CaptchaOptions
from datetime import datetime, timedelta

from pyTelegramBotCAPTCHA.telebot_captcha import languages
languages['en']['text'] = 'Welcome, #USER!\nPlease enter the code to verify that you are not a bot. You have 3 minutes.'

MAX_ATTEMPTS = 5
with open('bot_token.txt', 'r') as botTokenFile:
    BOT_TOKEN = botTokenFile.read().strip()

bot = TeleBot(BOT_TOKEN)
captcha_manager = CaptchaManager(
    bot_id=bot.get_me().id,
    default_options=CaptchaOptions(
        generator="default",
        timeout=180,
        code_length=5,
        max_attempts=MAX_ATTEMPTS,
        only_digits=True,
    ),
)

def is_enabled_for_group(chat_id: int) -> bool:
    return True  # TODO: restrict by chat ids


@bot.message_handler(content_types=["new_chat_members"])
def new_member(message):
    if not is_enabled_for_group(message.chat.id):
        return
    for user in message.new_chat_members:
        captcha_manager.restrict_chat_member(bot, message.chat.id, user.id)
        captcha_manager.send_new_captcha(bot, message.chat, user)
        print(f'New user detected: chat_id={message.chat.id}, user_id: {user.id}')


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
    print(f'User solved captcha: chat_id={captcha.chat.id}, user_id: {captcha.user.id}')


@captcha_manager.on_captcha_not_correct
def on_not_correct(captcha):
    if not is_enabled_for_group(captcha.chat.id):
        return
    if captcha.previous_tries < MAX_ATTEMPTS:
        captcha_manager.refresh_captcha(bot, captcha)
    else:
        bot.kick_chat_member(
            captcha.chat.id,
            captcha.user.id,
            until_date=(datetime.now() + timedelta(hours=1)),
        )
        captcha_manager.delete_captcha(bot, captcha)
        print(f'User failed ALL attempts to solve captcha and was kicked: previous_tries={captcha.previous_tries}, chat_id={captcha.chat.id}, user_id: {captcha.user.id}')


@captcha_manager.on_captcha_timeout
def on_timeout(captcha):
    if not is_enabled_for_group(captcha.chat.id):
        return
    bot.kick_chat_member(
        captcha.chat.id,
        captcha.user.id,
        until_date=(datetime.now() + timedelta(hours=1)),
    )
    captcha_manager.delete_captcha(bot, captcha)
    print(f'User failed to solve captcha in time and was kicked: chat_id={captcha.chat.id}, user_id: {captcha.user.id}')


if __name__ == '__main__':
    bot.polling()
