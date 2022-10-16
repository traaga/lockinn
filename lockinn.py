from sqlite3 import connect
import time
import json
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

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

def sendMessage(message):
    base_url = "https://api.telegram.org/bot"
    token = "5086600475:AAF9TbaQqO3TFs5TPQ7-3B0LpF1jukpk2z4"
    chat_id = "-662143411"

    request = base_url + token + "/sendMessage?chat_id=" + chat_id + "&text=" + str(message)
    requests.get(request)

def getMessages():
    base_url = "https://api.telegram.org/bot"
    token = "5086600475:AAF9TbaQqO3TFs5TPQ7-3B0LpF1jukpk2z4"
    
    for i in range(3):
        data = "data"
        now = time.strftime("%H:%M:%S", time.localtime())
        try:
            if i:
                print(f"{i+1}. getMessages() - {now}")
                
            request = base_url + token + "/getUpdates"
            r = requests.get(request)

            my_json = r.content.decode('utf8')
            data = json.loads(my_json)

            if "result" not in data:
                print(f"Data: {data}")

            return data["result"]

        except BaseException:
            print(f"BaseException({i+1}): Data - {data}")
            now = time.strftime("%H:%M:%S", time.localtime())
            logging.exception(f"getMessages() - {now}")
            if i == 2:
                return []
        time.sleep(10)

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

try:
    setup = True
    runBot = True
    runCheck = False
    checkDelay = 600 # sekundit
    referenceTime = time.time()
    referenceDate = datetime.now().strftime("%d.%m.%y")
    latest_update_id = max([ message["update_id"] for message in getMessages() ] or [0])
    latest_reservations = []

    sendMessage("Alustan tööd.\n/start, /stop, /list")

    while runBot:

        messages = getMessages()

        for message in messages:
            if message["update_id"] > latest_update_id:
                latest_update_id = message["update_id"]
                text = message["message"]["text"]
                print(text)

                if text == "/start":
                    runCheck = True
                    referenceTime = time.time() - checkDelay
                    latest_reservations = getReservations()
                    sendMessage("Alustan kontrollimist.")
                elif text == "/stop":
                    runCheck = False
                    sendMessage("Lõpetan kontrollimise.")
                elif text == "/kill":
                    runBot = False
                    sendMessage("Lõpetan töö.")
                    break
                elif text == "/list":
                    list = prettifyReservations(getReservations())
                    sendMessage(list)

        if runBot and runCheck and time.time() - referenceTime >= checkDelay:
            referenceTime = time.time()

            reservations = getReservations() # katki max retries exceeded

            todayDate = datetime.now().strftime("%d.%m.%y")

            if referenceDate == todayDate:
                checkForChanges(latest_reservations, reservations)

            latest_reservations = reservations

        time.sleep(3)
except BaseException:
    sendMessage("Midagi läks valesti ( ✖╭╮✖ ).")
    now = time.strftime("%H:%M:%S", time.localtime())
    logging.exception(f"Program Exit - {now}")
