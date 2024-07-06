#! python3.4

import datetime
import json
import os
import os.path
import random
import re
import shlex
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.request


class Logger(threading.Thread):
    def __init__(self, std_stream):
        self.console = std_stream
        self.with_lock = std_stream == sys.stderr
        if self.with_lock:
            super().__init__()
        try:
            Logger.log
        except AttributeError:
            log_name = SCRIPT_NAME + ".log"
            if not os.path.exists(log_name):
                with open(log_name, "w", encoding="utf_8_sig") as f:
                    f.write("")
            Logger.log = open(log_name, "r+", encoding="utf8", newline="\n")
            Logger.new_process = True
            Logger.LAST_LINE_TEXT = ": Скрипт проработал: "
            Logger.timedelta_tail = re.compile(":[^:]*$")
            Logger.days = re.compile(r"(\d+) (days?), \d")
            Logger.last_line = re.compile(r"[\s\S]*((20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]) " +
                r"(?:[01]\d|2[0-3])(?::[0-5]\d){2}(?:\.\d{6})?)" + Logger.LAST_LINE_TEXT +
                r"(?:\d+ (?:день|дня|дней), )?(?:1?\d|2[0-3]):[0-5]\d\.{3}\n$)")
    
    def write_last_line(self):
        def delta_str(time_delta):
            time_delta_string = str(time_delta)
            match = Logger.days.match(time_delta_string)
            if match is not None:
                number_of_days = "0" + match.group(1)
                return time_delta_string.replace(match.group(2),
                    "день" if number_of_days[-1] == "1" and number_of_days[-2] != "1" else
                    "дня" if number_of_days[-1] in "234" and number_of_days[-2] != "1" else "дней")
            return time_delta_string
        
        now = datetime.datetime.now()
        Logger.log.write(str(now) + Logger.LAST_LINE_TEXT +
            Logger.timedelta_tail.sub("", delta_str(now + datetime.timedelta(seconds=0.1) - start_time)) + "...\n")
        Logger.log.truncate()
    
    def set_pos(self, starting_script=False):
        Logger.log.seek(0, 2)
        if starting_script:
            Logger.new_process = False
            return
        pos = max(3, Logger.log.tell() - 87)
        for i in range(5):
            Logger.log.seek(pos)
            try:
                tail = Logger.log.read()
                break
            except UnicodeDecodeError:
                pos += 1
        else:
            Logger.log.seek(0, 2)
            tail = ""
        match = Logger.last_line.match(tail)
        if match is not None:
            if not Logger.new_process or datetime.datetime.now() - datetime.datetime.strptime(match.group(2),
                "%Y-%m-%d %H:%M:%S.%f") < datetime.timedelta(minutes=1.3):
                Logger.log.seek(Logger.log.tell() - len(match.group(1).encode("utf-8")))
        if Logger.new_process:
            Logger.new_process = False
    
    def execute(self, func, *args, **kwargs):
        if self.with_lock:
            with print_lock:
                func(*args, **kwargs)
        else:
            func(*args, **kwargs)
    
    def write(self, message):
        def write_(message):
            self.console.write(message)
            self.set_pos(message==FIRST_LOG_LINE)
            Logger.log.write(message)
            self.write_last_line()
        
        self.execute(write_, message)
        self.flush()
    
    def flush(self):
        def flush_():
            self.console.flush()
            Logger.log.flush()
        
        self.execute(flush_)
    
    def run(self):
        i = 0
        while True:
            i += 1
            now = datetime.datetime.now()
            next_update_time = start_time + datetime.timedelta(minutes=i)
            if now > next_update_time:
                continue
            time.sleep((next_update_time - now).total_seconds())
            with print_lock:
                self.set_pos()
                self.write_last_line()
            self.flush()


def hasten_site():
    global local_errors
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.verify_mode = ssl.CERT_NONE
    ssl_handler = urllib.request.HTTPSHandler(context=context)
    opener = urllib.request.build_opener(ssl_handler)
    while True:
        for i in range(3):
            for page in HASTENED_PAGES:
                try:
                    opener.open("https://" + SITE_LOCAL_ADDRESS + page, timeout=30)
                except Exception as err:
                    current_error = str(err)
                    for error in local_errors:
                        if error == current_error:
                            break
                    else:
                        local_errors.append(current_error)
                        with open(HS_ERRORS, "a") as msg_file:
                            msg_file.write(str(datetime.datetime.now()) + ": " + current_error + "\n")
                time.sleep(1)
        time.sleep(random.randint(120, 300))


def get_router_status():
    auth_handler = urllib.request.HTTPBasicAuthHandler()
    auth_handler.add_password("TP-LINK Wireless N Router WR841N", ROUTER_ADDRESS + "/", ROUTER_LOGIN, ROUTER_PASSWORD)
    cookie_processor = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(auth_handler, cookie_processor)
    opener.open(ROUTER_ADDRESS, timeout=10)
    opener.addheaders = [("Referer", ROUTER_ADDRESS)]
    response = opener.open(ROUTER_ADDRESS + STATUS_PAGE, timeout=10)
    opener.close()
    match = re.search(r"var wanPara = new Array\(\n([^<]+)\);\n</SCRIPT>", str(response.read(), "iso-8859-1"))
    if match is not None:
        wan_para = json.loads("[" + match.group(1) + "]")
        days, online_time = wan_para[STATUS_ONLINE_TIME].split(" day(s) ")
        online_time = datetime.datetime.strptime(online_time, "%H:%M:%S")
        online_time = datetime.timedelta(days=int(days), hours=online_time.hour, minutes=online_time.minute, seconds=online_time.second)
        return online_time, int(wan_para[STATUS_WAN_CONNECTED]), wan_para[STATUS_WAN_IP_ADDRESS]
    return None, None, None


def get_ip_address():
    global check_ip_error, last_got_ip_address, last_updated_ip_address
    last_got_ip_address = None
    last_updated_ip_address = prev_ip_address
    while True:
        time.sleep(ROUTER_CHECK_INTERVAL)
        try:
            online_time, wan_status, ip_address = get_router_status()
        except Exception:
            check_ip_error = True
            continue
        check_ip_error = False
        if wan_status != 1:
            continue
        last_got_ip_address = status + ip_address
        if last_updated_ip_address != last_got_ip_address:
            last_updated_ip_address = last_got_ip_address
            if last_got_ip_address == prev_ip_address:
                continue
            if status is not None:
                update_dyndns_address_thread = threading.Thread(target=update_dyndns_address, args=(last_got_ip_address, ))
                update_dyndns_address_thread.daemon = True
                update_dyndns_address_thread.start()


def idna(s):
    "Преобразует список адресов хостов в punycode"
    return ",".join(map(lambda x: x.encode("idna").decode("iso-8859-1"), s.split(",")))


def update_dyndns_address(status_and_new_address):
    def get_ip_address():
        global last_updated_ip_address
        if last_got_ip_address is not None and not check_ip_error:
            return status + last_got_ip_address[1:]
        last_updated_ip_address = None
        return None

    global prev_ip_address
    with dyndns_update_lock:
        offline = status_and_new_address.startswith("-")
        offline_state = "&offline=yes" if offline else ""
        prev_ip_address_at_update_start = prev_ip_address
        new_address = status_and_new_address[1:]
        regexp_tail = r"\r?\n?){{{}}}$".format(len(DYNDNS_HOST_NAMES.split(",")))
        NEXT_UPDATE_MSG = "    Следующая попытка обновления через "
        ERROR_MSG = ": Ошибка {0}при обновлении DynDNS: "
        off = " ({0})".format(offline_state[1:]) if offline else ""
        ver = DYNDNS_CLIENT_VERSION.split("/")[1]
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(capath=CA_CERTIFICATES_PATH)
        ssl_handler = urllib.request.HTTPSHandler(context=context)
        auth_handler = urllib.request.HTTPBasicAuthHandler()
        auth_handler.add_password(*("DynDNS API Access", DYNDNS_MEMBERS + "/", DYNDNS_USER, DYNDNS_PASSWORD))
        opener = urllib.request.build_opener(ssl_handler, auth_handler)
        opener.addheaders = [("User-Agent", DYNDNS_CLIENT_VERSION)]
        while True:
            try:
                with open(DYNDNS_NEXT_UPDATE_FILE) as f:
                    next_update_time = datetime.datetime.strptime(f.read().strip(), "%Y-%m-%dT%H:%M:%S")
            except Exception:
                next_update_time = None
            now = datetime.datetime.now()
            if next_update_time is not None and next_update_time > now + datetime.timedelta(seconds=1):
                with print_lock:
                    print(str(now) + ": Ожидание начала обновления DynDNS до " + str(next_updat_time) + "...")
                time.sleep((next_update_time-now).total_seconds())
            ip_address = get_ip_address()
            if ip_address is None or ip_address != status_and_new_address or prev_ip_address_at_update_start != prev_ip_address or os.path.exists(DYNDNS_UPDATE_ERROR_FILE):
                with print_lock:
                    print(str(datetime.datetime.now()) + ": " + new_address + off + ": Отмена обновления DynDNS...")
                return
            try:
                with print_lock:
                    print(str(datetime.datetime.now()) + ": " + new_address + off + ": Выполняется обновление DynDNS/" + ver + "...")
                response = opener.open(DYNDNS_MEMBERS + "/nic/update?hostname=" + DYNDNS_HOST_NAMES + "&myip=" + new_address +
                                       offline_state, timeout=20)
            except ssl.SSLError as error:
                with print_lock, open(DYNDNS_UPDATE_ERROR_FILE, "a") as err_file:
                    print(str(datetime.datetime.now()) + ": " + new_address + off + ERROR_MSG.format("SSL ") + str(error))
                    err_file.write(str(datetime.datetime.now()) + ": " + status_and_new_address + ": SSLError: " +
                                   str(error) + "\n")
                return
            except socket.error as error:
                with print_lock, open(DYNDNS_NEXT_UPDATE_FILE, "w") as f:
                    print(str(datetime.datetime.now()) + ": " + new_address + off + ERROR_MSG.format("") + str(error))
                    print(NEXT_UPDATE_MSG + str(DYNDNS_UPDATE_INTERVAL[0]) + " " + DYNDNS_UPDATE_INTERVAL[1] + "...")
                    f.write((datetime.datetime.now().replace(microsecond=0)+datetime.timedelta(minutes=DYNDNS_UPDATE_INTERVAL[0])).isoformat())
                time.sleep(DYNDNS_UPDATE_INTERVAL[0]*60)
                continue
            finally:
                opener.close()
            return_code = str(response.read(), "iso-8859-1", "replace")
            match = re.match(r"(dnserr|911)$", return_code)
            if match is not None:
                with print_lock, open(DYNDNS_NEXT_UPDATE_FILE, "w") as f:
                    print(str(datetime.datetime.now()) + ": " + new_address + off + ERROR_MSG.format("на сервере Dyn ") + match.group(1))
                    print(NEXT_UPDATE_MSG + str(DYNDNS_UPDATE_INTERVAL2[0]) + " " + DYNDNS_UPDATE_INTERVAL2[1] + "...")
                    f.write((datetime.datetime.now().replace(microsecond=0)+datetime.timedelta(minutes=DYNDNS_UPDATE_INTERVAL2[0])).isoformat())
                time.sleep(DYNDNS_UPDATE_INTERVAL2[0]*60)
                continue
            elif re.match("(?:good " + re.escape(new_address) + regexp_tail, return_code) is None:
                str_now = str(datetime.datetime.now())
                with print_lock, open(DYNDNS_UPDATE_ERROR_FILE, "a") as err_file:
                    print(str_now + ": " + new_address + off + ": Код возврата DynDNS: " + return_code + " (status: " + str(response.status) + ")")
                    err_file.write(str_now + ": " + return_code + " (status: " + str(response.status) + ")\n")
                return
            break
        update_monitor_odt_status_thread = threading.Timer(180, update_monitor_odt_status)
        update_monitor_odt_status_thread.daemon = True
        update_monitor_odt_status_thread.start()
        with print_lock:
            print(str(datetime.datetime.now()) + ": " + new_address + off + ": Успешное обновление DynDNS...")
            prev_ip_address = status_and_new_address
            try:
                with open(DYNDNS_IP_ADDRESS_FILE, "w") as f:
                    f.write(status_and_new_address)
            except Exception as error:
                with open(DYNDNS_UPDATE_ERROR_FILE, "a") as err_file:
                    err_file.write(str(datetime.datetime.now()) + ": " + status_and_new_address + ": .adr file: " + str(error) + "\n")


def update_monitor_odt_status():
    ODT_LOGIN_ADDRESS = "https://secured.online-domain-tools.com/user.login/"
    MONITOR_ADDRESS = "http://server-monitoring.online-domain-tools.com/"
    CHANGE_STATUS_DO = "changeStatePostLink-128w{0}-form-submit"
    CHANGE_STATUS_REGEX = r'<div class="show-when-js-is-off"><form action="/" method="post" id="([^"]+)">.*?name="do" value="' + CHANGE_STATUS_DO + '">'
    LOGOUT_DO = "userBar-logoutPostLink-form-submit"
    LOGOUT_REGEX = r'<div class="show-when-js-is-off"><form action="/" method="post" id="([^"]+)">.*?name="do" value="' + LOGOUT_DO + '">'
    ERROR_MESSAGE_STATUS = "шаг {0}: статус {1}!!!"
    ERROR_MESSAGE_MATCH = "шаг {0}: не обнаружен ID!!!"
    ENCODING = "utf-8"
    TIMEOUT = 20
    read = lambda x: str(x.read(), ENCODING, "replace")
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(capath=CA_CERTIFICATES_PATH)
    ssl_handler = urllib.request.HTTPSHandler(context=context)
    cookie_processor = urllib.request.HTTPCookieProcessor()
    redirect_handler = urllib.request.HTTPRedirectHandler()
    opener = urllib.request.build_opener(ssl_handler, cookie_processor, redirect_handler)
    with odt_status_update_lock:
        try:
            response = opener.open(ODT_LOGIN_ADDRESS, timeout=TIMEOUT)
            if response.status != 200:
                raise Exception(ERROR_MESSAGE_STATUS.format(1, response.status))
            parms = urllib.parse.urlencode(dict(email=ODT_EMAIL, password=ODT_PASSWORD))
            opener.addheaders = [("Referer", ODT_LOGIN_ADDRESS)]
            response = opener.open(ODT_LOGIN_ADDRESS + "?do=loginForm-submit", parms.encode(ENCODING), timeout=TIMEOUT)
            if response.status != 200:
                raise Exception(ERROR_MESSAGE_STATUS.format(2, response.status))
            response = opener.open(MONITOR_ADDRESS, timeout=TIMEOUT)
            if response.status != 200:
                raise Exception(ERROR_MESSAGE_STATUS.format(3, response.status))
            match = re.search(CHANGE_STATUS_REGEX.format(0), read(response))
            if match is None:
                raise Exception(ERROR_MESSAGE_MATCH.format(3))
            parms = urllib.parse.urlencode(dict(id = match.group(1), do = CHANGE_STATUS_DO.format(0)))
            opener.addheaders = [("Referer", MONITOR_ADDRESS)]
            response = opener.open(MONITOR_ADDRESS, parms.encode(ENCODING), timeout=TIMEOUT)
            if response.status != 200:
                raise Exception(ERROR_MESSAGE_STATUS.format(4, response.status))
            match = re.search(CHANGE_STATUS_REGEX.format(1), read(response))
            if match is None:
                raise Exception(ERROR_MESSAGE_MATCH.format(4))
            parms = urllib.parse.urlencode(dict(id = match.group(1), do = CHANGE_STATUS_DO.format(1)))
            time.sleep(10)
            response = opener.open(MONITOR_ADDRESS, parms.encode(ENCODING), timeout=TIMEOUT)
            if response.status != 200:
                raise Exception(ERROR_MESSAGE_STATUS.format(5, response.status))
            with print_lock:
                print(str(datetime.datetime.now()) + ": Обновлен статус монитора odt...")
            match = re.search(LOGOUT_REGEX, read(response))
            if match is None:
                raise Exception(ERROR_MESSAGE_MATCH.format(5))
            parms = urllib.parse.urlencode(dict(id = match.group(1), do = LOGOUT_DO))
            response = opener.open(MONITOR_ADDRESS, parms.encode(ENCODING), timeout=TIMEOUT)
        except Exception as err:
            with print_lock:
                print(str(datetime.datetime.now()) + ": Ошибка при обновлении статуса монитора odt: " + str(err))

        
if __name__ == "__main__":
    SCRIPT_NAME = os.path.splitext(__file__)[0]
    CA_CERTIFICATES_PATH = "/etc/ca-certificates/extracted/cadir/"
    FIRST_LOG_LINE = "\n{0:=^65}".format("")

    # Доступ к роутеру
    ROUTER_ADDRESS = "http://192.168.0.1:8008"
    STATUS_PAGE = "/userRpm/StatusRpm.htm"
    STATUS_WAN_IP_ADDRESS = 2
    STATUS_ONLINE_TIME = 12
    STATUS_WAN_CONNECTED = 13
    ROUTER_CHECK_INTERVAL = 60 # секунд

    # Параметры, используемые клиентом DynDNS
    # http://www.dyndns.com/developers/routers/hints.html
    DYNDNS_CLIENT_VERSION = "Konstantin Kulakov-Monitor_linux_user.py/2.08"
    DYNDNS_MEMBERS = "https://members.dyndns.org"
    DYNDNS_UPDATE_INTERVAL = 10, "минут"  # Ожидание перед повтором попытки обновления адреса при отсутствии ответа сервера
    DYNDNS_UPDATE_INTERVAL2 = 30, "минут"  # Ожидание в случаях проблем на серверах Dyn
    DYNDNS_UPDATE_ERROR_FILE = SCRIPT_NAME + ".err"
    DYNDNS_DATA_FILE = SCRIPT_NAME + ".dat"
    DYNDNS_NEXT_UPDATE_FILE = SCRIPT_NAME + ".next"
    DYNDNS_IP_ADDRESS_FILE = SCRIPT_NAME + ".adr"
    DYNDNS_OFFLINE_FILE = SCRIPT_NAME + ".off"
    STATIC_ADDRESS = False

    # Ускорение доступа к сайту
    SITE_LOCAL_ADDRESS = "localhost"
    HASTENED_PAGES = "/community/notices/", "/community/news/"
    HS_ERRORS = SCRIPT_NAME + ".hs.err"

    start_time = datetime.datetime.now()
    count = 0
    try:
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(SCRIPT_NAME + ".log"))
    except Exception:
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(__file__))
    while start_time < mtime:
        time.sleep(30)
        count += 1
        start_time = datetime.datetime.now()
    
    print_lock = threading.Lock()
    dyndns_update_lock = threading.Lock()
    odt_status_update_lock = threading.Lock()
   
    sys.stdout = Logger(sys.stdout)
    sys.stderr = Logger(sys.stderr)
    sys.stderr.daemon = True
    sys.stderr.start()
    
    with print_lock:
        print(FIRST_LOG_LINE)
        if count:
            delta = datetime.timedelta(minutes=.5*count)
            print(str(start_time) + ": Выполнено ожидание установки времени в течение: " + str(delta) + "...")
        print(str(start_time) + ": Начало работы скрипта...")
    
    try:
        with open(DYNDNS_IP_ADDRESS_FILE) as f:
            prev_ip_address = f.read().strip()
    except Exception:
        prev_ip_address = None

    try:
        local_errors = []
        with open(DYNDNS_DATA_FILE) as f:
            temp, DYNDNS_USER, DYNDNS_PASSWORD, ODT_EMAIL, ODT_PASSWORD, ROUTER_LOGIN, ROUTER_PASSWORD = f.read().strip().split(" ")
        DYNDNS_HOST_NAMES = idna(temp)
        del temp
        status = "-" if os.path.exists(DYNDNS_OFFLINE_FILE) else "+"
        get_ip_address_thread  = threading.Thread(target=get_ip_address)
        get_ip_address_thread.daemon = True
        get_ip_address_thread.start()
    except Exception:
        status = None

    hasten_site_thread = threading.Timer(60, hasten_site)
    hasten_site_thread.daemon = True
    hasten_site_thread.start()

    try:
        subprocess.check_output(shlex.split("/bin/cec-client -s -d 1"), input=b"q\n")
    except Exception as err:
        with print_lock:
            print(str(datetime.datetime.now()) + ": Ошибка при отключении устройства AnyNet+: " + str(err) + "!!!")
    
    while True:
        status = "-" if os.path.exists(DYNDNS_OFFLINE_FILE) else "+"
        #now = datetime.datetime.now()
        #if now.minute == 5:
        #    update_monitor_odt_status()
        #    time.sleep(60)
        time.sleep(5)
