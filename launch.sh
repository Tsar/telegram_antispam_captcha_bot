#!/bin/bash -e

python3.8 captcha_gatekeeper_bot.py 2>&1 | tee -a captcha_bot_logs.txt
