#! python3.4

import datetime
import itertools
import os
import os.path
import re
import shlex
import subprocess
import sys
import threading
import time


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
        try:
            Logger.log.write(str(now) + Logger.LAST_LINE_TEXT +
                Logger.timedelta_tail.sub("", delta_str(now + datetime.timedelta(seconds=0.1) - start_time)) + "...\n")
        except Exception:
            pass
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


def check_eth0():
    ERROR_COUNT = 3
    prev_ip_address = ""
    while True:
        match = INET_REGEXP.search(str(subprocess.check_output(shlex.split("/sbin/ifconfig"))))
        if match is not None:
            new_ip_address = match.group(1)
            if new_ip_address is not None:
                count = ERROR_COUNT
            if new_ip_address != prev_ip_address:
                if new_ip_address is None:
                    count -= 1
                    if not count:
                        with print_lock:
                            print(str(datetime.datetime.now()) + ": Не задан ip адрес!!!")
                        prev_ip_address = new_ip_address
                else:
                    with print_lock:
                        print(str(datetime.datetime.now()) + ": Получен ip адрес: " + new_ip_address)
                    prev_ip_address = new_ip_address
        time.sleep(15)


def modify_django_settings():
    with open(IP_ADDRESS_FILE, "r") as f:
        new_ip_address = f.read()[1:]

    with open(DJANGO_SETTINGS_FILE, "r", encoding="utf_8_sig") as i, open(DJANGO_NEW_SETTINGS_FILE, "w", encoding="utf_8_sig") as o:
        for line in i:
            if line.startswith("ALLOWED_HOSTS"):
                line = ALLOWED_HOSTS.format(new_ip_address)
            o.write(line)
    os.replace(DJANGO_NEW_SETTINGS_FILE, DJANGO_SETTINGS_FILE)

    returncode = subprocess.call(shlex.split("/usr/bin/python -m compileall -f {0}".format(DJANGO_SETTINGS_FOLDER)))
    with print_lock:
        print(str(datetime.datetime.now()) + ": перекомпилированы установки django с результатом: {0}...".format(returncode))
    

    returncode = subprocess.call(shlex.split("/sbin/systemctl restart httpd"))
    with print_lock:
        print(str(datetime.datetime.now()) + ": веб-сервер перезапущен с результатом: {0}...".format(returncode))


if __name__ == "__main__":
    SCRIPT_NAME = os.path.splitext(__file__)[0]
    FIRST_LOG_LINE = "\n{0:=^65}".format("")
    INTERNET_SERVERS = "skype.com", "yandex.com", "google.com"
    INET_REGEXP = re.compile(r"eth0:[^\n]+?\\n\s+(?:inet\s(\S+)\s[^\n]+?\\n\s+)?ether")
    IP_ADDRESS_FILE = "/home/user/scripts/Monitor_linux_user/Monitor_linux_user.adr"
    DJANGO_SETTINGS_FOLDER = "/srv/home_site/home_site"
    DJANGO_SETTINGS_FILE = os.path.join(DJANGO_SETTINGS_FOLDER, "settings.py")
    DJANGO_NEW_SETTINGS_FILE = DJANGO_SETTINGS_FILE + ".new"
    ALLOWED_HOSTS = "ALLOWED_HOSTS = ('localhost', 'alarmpi', 'xn--d1aqf.dyndns.org', 'www.xn--d1aqf.dyndns.org', '{0}')\n"


    start_time = datetime.datetime.now()
    count = 0
    server = itertools.cycle(INTERNET_SERVERS)
    ntpd_cycle = itertools.cycle(range(20))
    try:
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(SCRIPT_NAME + ".log"))
    except Exception:
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(__file__))
    while start_time < mtime:
        try:
            if not subprocess.call(shlex.split("/usr/sbin/ping -4 -c 5 {0}".format(next(server))), timeout=10) and not (next(ntpd_cycle) - 2):
                subprocess.call(shlex.split("/sbin/killall ntpd"))
                subprocess.call(shlex.split("/sbin/ntpd -qg"))
        except subprocess.TimeoutExpired:
            pass
        time.sleep(30)
        count += 1
        start_time = datetime.datetime.now()
    
    print_lock = threading.Lock()
   
    sys.stdout = Logger(sys.stdout)
    sys.stderr = Logger(sys.stderr)
    sys.stderr.daemon = True
    sys.stderr.start()

    check_eth0_thread = threading.Timer(60, check_eth0)
    check_eth0_thread.daemon = True
    check_eth0_thread.start()

    with print_lock:
        print(FIRST_LOG_LINE)
        if count:
            delta = datetime.timedelta(minutes=.5*count)
            print(str(start_time) + ": Выполнено ожидание установки времени в течение: " + str(delta) + "...")
        print(str(start_time) + ": Начало работы скрипта...")
    
    returncode = subprocess.call(shlex.split("/sbin/systemctl start cronie"))
    with print_lock:
        print(str(datetime.datetime.now()) + ": Планировщик запущен с результатом: {0}...".format(returncode))
    returncode = subprocess.call(shlex.split("/sbin/systemctl start postgresql"))
    with print_lock:
        print(str(datetime.datetime.now()) + ": SQL сервер запущен с результатом: {0}...".format(returncode))
    returncode = subprocess.call(shlex.split("/sbin/systemctl start httpd"))
    with print_lock:
        print(str(datetime.datetime.now()) + ": веб-сервер запущен с результатом: {0}...".format(returncode))

    ip_address_change_time = None
    while True:
        test_time = os.stat(IP_ADDRESS_FILE).st_mtime
        if ip_address_change_time != test_time:
            if ip_address_change_time is not None:
                modify_django_settings()
            ip_address_change_time = test_time
        time.sleep(5)
