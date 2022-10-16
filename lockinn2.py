#!/usr/bin/env python

from sqlite3 import connect
import time
import json
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

token = "5086600475:AAF9TbaQqO3TFs5TPQ7-3B0LpF1jukpk2z4"

def startChecking(update, context):
    update.message.reply_text('Start!')

def stopChecking(update, context):
    update.message.reply_text("Stop!")

def displayReservations(update, context):
    currentReservations = prettifyReservations(getReservations())
    update.message.reply_text(currentReservations)

def killTheBot(update, context):
    update.message.reply_text("Kill!")

def errorHandling(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def getReservations():
    url = "https://lockinn.ee/wp-admin/admin-ajax.php"
    login_url = "https://lockinn.ee/wp-login.php"
    user_agent = "Chrome/94.0.4606.81"

    date = datetime.now().strftime("%Y-%m-%d")

    data = {
        "action": "booked_admin_calendar_date",
        "date": date,
        "pll_ajax_backend": "1"
    }

    login_data = {
        "log": "lockinn",
        "pwd": "Vanemuise65!",
        "wp-submit": "Logi sisse",
        "redirect_to": "https://lockinn.ee/wp-admin/",
        "testcookie": "1"
    }

    session = requests.Session()
    session.headers["User-Agent"] = user_agent

    retry = Retry(connect=3, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    session.post(login_url, login_data)
    r = session.post(url, data)

    soup = BeautifulSoup(r.content, "html.parser")

    tabs = soup.find_all("div", attrs = {"class": "bookedAppointmentTab"})

    reservations = {}

    for tab in tabs:
        soup2 = BeautifulSoup(str(tab), "html.parser")
        title_raw = soup2.find("h2").text
        timeslots = soup2.find_all("div", attrs = {"class": "timeslot"})
        title = title_raw.strip().split()[0]
        reservations[title] = {}
        for timeslot in timeslots:
            t = timeslot.text.strip()[:13]
            reservations[title][t] = ""
            txt = timeslot.text.strip().split()
            if len(txt) > 6:
                reservations[title][t] = timeslot.text.strip().split()[6]

    return reservations

def checkForChanges(a,b):
    if a != b:
        if a.keys() == b.keys():
            for room in a.keys():
                if a[room].keys() == b[room].keys():
                    for t in a[room].keys():
                        if a[room][t] != b[room][t]:
                            if a[room][t] == "":
                                sendMessage(f"Lisati broneering: {room} {t} {b[room][t]}")
                            elif b[room][t] == "":
                                sendMessage(f"Broneering tühistati: {room} {t}")
                            else:
                                sendMessage(f"Broneering muudeti: {room} {t} {a[room][t]} -> {room} {t} {b[room][t]}")
                else:
                    sendMessage(f"Ajad ei kattu: {list(a[room].keys())} =/= {list(b[room].keys())}")
        else:
            sendMessage(f"Toad ei kattu: {list(a.keys())} =/= {list(b.keys())}")

def prettifyReservations(reservations):
    result = datetime.now().strftime("%d.%m.%y %H:%M:%S") + "\n"
    for room in reservations:
        result += f"{room}:\n"
        for t in reservations[room]:
            if reservations[room][t]:
                result += f"   {t} {reservations[room][t]}\n"
            else:
                result += f"   {t} -\n"

    return result.strip()


def main():
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", startChecking))
    dp.add_handler(CommandHandler("stop", startChecking))
    dp.add_handler(CommandHandler("list", displayReservations))
    dp.add_handler(CommandHandler("kill", killTheBot))

    dp.add_error_handler(errorHandling)

    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
