#! python3.3

import configparser
import ctypes
import datetime
import functools
import getpass
import gettext
import ibm_db
import itertools
import json
import multiprocessing
import os
import pickle
import psutil
import pythoncom
import pywintypes
import queue
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import win32api
import win32com.client
import win32con
import win32console
import win32crypt
import win32gui
import winreg
import winsound


class TestUPS(threading.Thread):
    def __init__(self):
        super().__init__()
        self.all_right = False
        self._test = self._test_ups_status()
    
    def run(self):
        pythoncom.CoInitialize()
        while True:
            try:
                self.all_right = next(self._test) == 0
            except StopIteration:
                break
        self.all_right = False
    
    def _test_ups_status(self):
        global start_agent
        IPPON_SERVICES = "UPSmonitor", "UPSRMI"
        QUERY1 = "Select Name, State from Win32_Service where Name like 'UPS%'"
        QUERY2 = r"Select Name from Win32_Process where ExecutablePath like '%\\MonitorSoftware\\%'"
        UPS_USER_PROCESSNAMES = {"UPSMS.exe", "javaw.exe"}
        wmi = win32com.client.GetObject(MONIKER)
        while True:
            status = 0
            d = datetime.datetime.now()
            try:
                items = wmi.ExecQuery(QUERY1, "WQL", 48)
            except Exception:
                status = -1
            else:
                try:
                    for item in items:
                        if item.Name in IPPON_SERVICES and item.State != "Running":
                            status = 1
                            break
                    else:
                        try:
                            items = wmi.ExecQuery(QUERY2)
                        except Exception:
                            status = -3
                        else:
                            try:
                                if not UPS_USER_PROCESSNAMES.issubset(map(lambda x: x.Name, items)):
                                    status = 2
                                    start_agent = True
                            except Exception:
                                status = -4
                except Exception:
                    status = -2
            finally:
                yield status
                time.sleep(UPS_TEST_PERIOD)


class Sound(threading.Thread):
    def __init__(self):
        super().__init__()
        self.alarm = False
    
    def run(self):
        while True:
            if self.alarm:
                winsound.MessageBeep(winsound.MB_ICONHAND)
            time.sleep(1)


def speak_warning():
    global speak_russian
    pythoncom.CoInitialize()
    ENGLISH_VOICE = re.compile(r"\bEnglish\b")
    RUSSIAN_VOICE = re.compile(r"\b\RUS\b")
    sp_voice = win32com.client.Dispatch("SAPI.SpVoice")
    sp_voice.Volume = 100
    sp_voice.Rate = -1
    for voice in sp_voice.GetVoices():
        if ENGLISH_VOICE.search(voice.GetDescription()) is not None:
            default_voice = voice
            break
    if RUSSIAN_VOICE.search(sp_voice.Voice.GetDescription()) is None:
        for voice in sp_voice.GetVoices():
            if RUSSIAN_VOICE.search(voice.GetDescription()) is not None:
                sp_voice.Voice = voice
                sp_voice.Speak("Сообщения могут произноситься по-русски, выбери русский голос для преобразования текста в речь в панели управления")
                break
        if ENGLISH_VOICE.search(voice.GetDescription()) is None:
            sp_voice.Voice = default_voice
        speak_russian = speak_russian_local = False
    else:
        speak_russian = speak_russian_local = True
    while True:
        if speak_russian != speak_russian_local:  # speak_russian == False
            sp_voice.Voice = default_voice
            speak_russian_local = speak_russian
        if shutdown_started and shutdown is not None:
            try:
                if shutdown:
                    sp_voice.Speak(_("shutdown started"))
                else:
                    sp_voice.Speak(_("reboot started"))
            except pywintypes.com_error:
                pass
        else:
            try:
                message = speaker_queue.get_nowait()
                if SPEAKER_START_TIME <= datetime.datetime.now().time() < SPEAKER_STOP_TIME:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK if message.endswith("!") else winsound.MB_ICONEXCLAMATION)
                    try:
                        sp_voice.Speak(message)
                    except pywintypes.com_error:
                        pass
            except queue.Empty:
                pass
            time.sleep(1)
            continue
        time.sleep(30)


@functools.lru_cache()
def full_path(filename):
    try:
        return '"' + win32api.SearchPath(None, filename, ".exe")[0] + '"'
    except pywintypes.error:
        return filename


def get_reg_key(sub_key=r"Software\Monitor2", create=False, access=winreg.KEY_READ):
    if isinstance(sub_key, str):
        key = winreg.HKEY_CURRENT_USER
    elif isinstance(sub_key, tuple) and len(sub_key) == 2:
        key, sub_key = sub_key
    else:
        return None
    if create:
        try:
            reg_key = winreg.CreateKey(key, sub_key)
        except WindowsError:
            return None
    else:
        try:
            reg_key = winreg.OpenKey(key, sub_key, access=access)
        except WindowsError:
            return None
    return reg_key


def get_time_from_reg(reg_key, value_name):
    try:
        return datetime.datetime.strptime(winreg.QueryValueEx(reg_key, value_name)[0], "%Y-%m-%dT%H:%M:%S")
    except Exception as error:
        if error.args[0] != 2:
            print(value_name + ":", error, "...")
        return None

    
def update_time_in_reg(reg_key, value_name, date_time):
    try:
        winreg.SetValueEx(reg_key, value_name, 0, winreg.REG_SZ, date_time.isoformat()[:19])
    except WindowsError as error:
        print(value_name + ":", error, "!!!")

    
def shutdown_computer(abort_shutdown=False):
    global shutdown_started, shutdown
    LAST_REBOOT = "LastReboot"
    PREV_REBOOT = "PrevReboot"
    message = "Потеряна связь с ИБП. {0} компьютера через 1 минуту..."
    parameters = ' {0} /t 60 /d u:6:12 /c "{1}"'
    
    now = datetime.datetime.now()
    dt = str(now) + ": "
    with print_lock, get_reg_key(access=winreg.KEY_ALL_ACCESS) as reg_key:
        if abort_shutdown:
            try:
                winreg.DeleteValue(reg_key, LAST_REBOOT) 
            except WindowsError as error:
                if error.args[0] != 2:
                    print(LAST_REBOOT + ":", error, "!!!")
            parameters = ' /a'
            shutdown = None
            print(dt + "Завершение работы компьютера отменено.")
        else:
            last_reboot_time = get_time_from_reg(reg_key, LAST_REBOOT)
            prev_reboot_time = get_time_from_reg(reg_key, PREV_REBOOT)
            if (last_reboot_time and now - last_reboot_time <= datetime.timedelta(minutes=15) and
                prev_reboot_time and now - prev_reboot_time <= datetime.timedelta(minutes=30)):
                    message = message.format("Выключение")
                    parameters = parameters.format("/s", message)
                    shutdown = True
            else:
                message = message.format("Перезагрузка")
                parameters = parameters.format("/r", message)
                shutdown = False
                if last_reboot_time:
                    update_time_in_reg(reg_key, PREV_REBOOT, last_reboot_time)
                update_time_in_reg(reg_key, LAST_REBOOT, now)
            print(dt + message)
    
    shutdown_started = not abort_shutdown
    subprocess.Popen(full_path('shutdown.exe') + parameters)


def get_voltage(time_stamp=False, last_time=None):
    def get_time(f, line_number):
        f.seek(line_number*RECORD_LENGTH)
        return(datetime.datetime.strptime(f.read(DATE_TIME_LENGTH), "%m/%d/%Y,%H:%M:%S"))
    
    global upsdata
    VOLTAGE = "Напряжение: "
    UNKNOWN = VOLTAGE + "???"
    INPUT_VOLTAGE_INDEX = 5
    OUTPUT_VOLTAGE_INDEX = 8
    RECORD_LENGTH = 81
    DATE_TIME_LENGTH = 19
    new_data = []
    RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        upsdata
    except NameError:
        try:
            upsdata = ["", (None, ""), ""]
            with get_reg_key((winreg.HKEY_LOCAL_MACHINE, RUN)) as reg_key:
                upsdata[2] = winreg.QueryValueEx(reg_key, "UPSMS")[0]
            upsdata[0] = os.path.join(os.path.split(upsdata[2])[0], "UPSDATA.CSV")
        except Exception:
            del upsdata
            return [] if last_time is not None else datetime.datetime.now() if time_stamp else UNKNOWN
    try:
        last_modified = os.stat(upsdata[0]).st_mtime
        if last_time is not None or upsdata[1][0] != last_modified:
            with open(upsdata[0], "r") as f:
                if last_time is not None:
                    record_count = int(os.path.getsize(upsdata[0])/RECORD_LENGTH) - 1
                    first = 0
                    last = record_count
                    if get_time(f, first) > last_time:
                        start = first
                    elif get_time(f, last) < last_time:
                        return []
                    else:
                        while first < last:
                            mid = int(first + (last - first) / 2)
                            if last_time <= get_time(f, mid):
                                last = mid
                            else:
                                first = mid + 1
                        start = last + (1 if last_time == get_time(f, last) else 0)
                    f.seek(start*RECORD_LENGTH)
                    for line in f.read().split("\n"):
                        if not len(line.strip()):
                            break
                        list_ = line.split(",")
                        local_time = datetime.datetime.strptime(",".join(list_[:2]), "%m/%d/%Y,%H:%M:%S")
                        hour_group = int((local_time - datetime.datetime(2000, 1, 1)) / datetime.timedelta(hours=1))
                        input_voltage = int(list_[INPUT_VOLTAGE_INDEX])
                        output_voltage = int(list_[OUTPUT_VOLTAGE_INDEX])
                        if output_voltage and 999 not in (input_voltage, output_voltage):
                            new_data.append((local_time, hour_group, input_voltage, output_voltage))
                    return new_data
                else:
                    f.seek(os.path.getsize(upsdata[0]) - RECORD_LENGTH)
                    data = f.read().strip().split(",", INPUT_VOLTAGE_INDEX + 1)
            data[0] = datetime.datetime.strptime(data[0], "%m/%d/%Y").date().isoformat()
            last_record_time = " ".join(data[:2])
            # В одном экземпляре скрипта применяется только один вариант вызова (параметр time_stamp)
            if time_stamp:
                data = datetime.datetime.strptime(last_record_time, "%Y-%m-%d %H:%M:%S")
            else:
                data = VOLTAGE + data[INPUT_VOLTAGE_INDEX] + " (" + last_record_time + ")"
            upsdata[1] = (last_modified, data)
        else:
            data = upsdata[1][1]
        return data
    except Exception:
        return [] if last_time is not None else datetime.datetime.now() if time_stamp else UNKNOWN


def update_site():
    def update_data():
        try:
            conn = ibm_db.connect(DB_NAME, "", "")
        except Exception:
            return False
        error = last_time = False
        try:
            start_date = datetime.date.today() - datetime.timedelta(days=365)
            select = "SELECT COUNT(*) FROM IPPON.VOLTAGE WHERE LOCAL_TIME < ?"
            stmt = ibm_db.prepare(conn, select)
            ibm_db.execute(stmt, (start_date, ))
            if ibm_db.fetch_tuple(stmt)[0]:
                delete = "DELETE FROM IPPON.VOLTAGE WHERE LOCAL_TIME < ?"
                stmt = ibm_db.prepare(conn, delete)
                ibm_db.execute(stmt, (start_date, ))
            select = "SELECT MAX(LOCAL_TIME) FROM IPPON.VOLTAGE"
            stmt = ibm_db.exec_immediate(conn, select)
            last_time = ibm_db.fetch_tuple(stmt)
            last_time = last_time[0] if last_time else datetime.datetime(2000, 1, 1)
            new_data = get_voltage(last_time=last_time)
            if new_data:
                insert = ("INSERT INTO IPPON.VOLTAGE (LOCAL_TIME, HOUR_GROUP, INPUT_VOLTAGE, OUTPUT_VOLTAGE)" +
                    " VALUES (?, ?, ?, ?)")
                stmt = ibm_db.prepare(conn, insert)
                ibm_db.execute_many(stmt, tuple(new_data))
            else:
                error = True
        except Exception as err:
            error = True
            n = 0
            message = ""
            err_list = re.split(r"(Error \d+:.*SQLSTATE=([\S]+).*)", str(err))
            for i in range(int(len(err_list)/3)):
                if err_list[i*3+2] == "23505":
                    n += 1
                else:
                    message += "\n    " + err_list[i*3+1]
            message = ": update_data:" + (" дублирующие записи в количестве: " + str(n) + ", начиная с " +
                str(last_time) + "\n    проигнорированы на SQL сервере при попытке вставки..." if n else "") + message
            with print_lock:
                print(str(datetime.datetime.now()) + re.sub(r"\r", "\r\n", message))
        ibm_db.close(conn)
        return not error
    
    MAX_ERR_NO = 40
    error_count = 0
    while True:
        update_status = update_data()
        now = datetime.datetime.now()
        if update_status:
            error_count = 0
        else:
            error_count += 1
            if error_count == MAX_ERR_NO:
                with print_lock:
                    print(str(now) + ": Проблемы с поступлением данных от ИБП на SQL сервер!!!")
                speaker_queue.put(_("New UPS data is not available on the SQL server!"))
        next_update_time = (now + datetime.timedelta(minutes=DB_UPDATE_INTERVAL - now.minute %
            DB_UPDATE_INTERVAL)).replace(second=0, microsecond=0)
        update_interval = ((next_update_time - now).total_seconds() if update_status else
            30 if error_count < MAX_ERR_NO else 900)
        time.sleep(update_interval)


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
            Logger.log = open(log_name, "r+", encoding="utf8", newline="\r\n")
            Logger.new_process = True
            Logger.LAST_LINE_TEXT = ": Скрипт проработал: "
            Logger.timedelta_tail = re.compile(":[^:]*$")
            Logger.days = re.compile(r"(\d+) (days?), \d")
            Logger.last_line = re.compile(r"[\s\S]*((20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]) " +
                r"(?:[01]\d|2[0-3])(?::[0-5]\d){2}\.\d{6})" + Logger.LAST_LINE_TEXT +
                r"(?:\d+ (?:день|дня|дней), )?(?:1?\d|2[0-3]):[0-5]\d\.{3}\r\n$)")
    
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
        
        if not keep_output:
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
        # i == 0  при смещении -87 для наиболее вероятного случая:
        # скрипт проработал 0 дней, выводимый текст оканчивается на r"[\u0401\u0410-\u044f\u0451]{6,}\.{3}(?:\r\n)?"
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
        if keep_output:
            return
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


def call_(cmdline):
    args = cmdline.split()
    if args[0].find("\\") == -1 and args[0].find(":") == -1:
        args[0] = full_path(args[0])
    cmdline = " ".join(args)
    with print_lock:
        print("    Выполняется команда " + (" ".join(args[:3])) + "...")
    try:
        process = subprocess.Popen(cmdline, bufsize=1, stdout=subprocess.PIPE)
    except WindowsError as error:
        with print_lock:
            print("call_: " + str(error))
        return -10101
    readline = process.stdout.readline
    line = True
    while process.poll() is None or line:
        line = readline()
        if line:
            with print_lock:
                print("    " + line.decode("cp866"), end="")
        else:
            time.sleep(0.1)
    return process.poll()


def modem_status():
    def get_status(reboot=False, full_info=False):
        try:
            auth_handler = urllib.request.HTTPBasicAuthHandler()
            auth_handler.add_password(*itertools.chain(("TD-8616", MODEM_ADDRESS + "/"),
                                                       pickle.loads(win32crypt.CryptUnprotectData(modem_credential,
                                                                                                  bytes(__file__, "utf-8"), None, None, 0)[1])))
            opener = urllib.request.build_opener(auth_handler)
            if reboot:
                opener.open(MODEM_ADDRESS + MODEM_REBOOT_PAGE, timeout=10)
                opener.close()
                return None
            response = opener.open(MODEM_ADDRESS + MODEM_STATUS_PAGE, timeout=10)
            opener.close()
            lines = response.readlines()
            process_state = process_snr = process_modulation = False
            process_rate = 0
            state = snr = data_rate = modulation = ""
            for line in lines[46:]:
                strline = str(line, encoding="iso-8859-1").strip()
                if process_state:
                    state = LINE_STATE_TEXT.sub("", strline)
                    process_state = False
                elif process_snr:
                    snr = strline[:strline.find(" ")]
                    if full_info:
                        process_snr = False
                    else:
                        break
                elif LINE_STATE.match(strline) is not None:
                    process_state = True
                elif SNR_MARGIN.match(strline) is not None:
                    process_snr = True
                if full_info:
                    if process_modulation:
                        modulation = " " + strline[:strline.find("<")]
                        process_modulation = False
                    elif process_rate:
                        data_rate += " " + strline[:strline.find("<")].strip()
                        process_rate -= 1
                    elif MODULATION.match(strline) is not None:
                        process_modulation = True
                    elif DATA_RATE.match(strline) is not None:
                        process_rate = 2
            return state, snr, data_rate.strip() + modulation
        except urllib.error.URLError as error:
            match = WIN_ERROR.search(str(error))
            if not (isinstance(error.reason, socket.timeout) or (match is not None and int(match.group(1)) in (10054, 10060, 10065))):
                str_error = str(error)
        except WindowsError as error:
            if not (isinstance(error, socket.timeout) or error.args[0] in (10054, 10060, 10065)):
                str_error = "w" + str(error)
        except Exception as error:
            str_error = str(sys.exc_info()[0]) + " (" + str(sys.exc_info()[1]) + ")"
        finally:
            opener.close()
        try:
            with print_lock:
                print(str(datetime.datetime.now()) + ": Ошибка при обращении к модему: " + str_error)
        except NameError:
            pass
        return "", "", ""

    global reconnect_internet_thread
    with print_lock, get_reg_key() as reg_key:
        try:
            modem_credential = winreg.QueryValueEx(reg_key, MODEM)[0]
        except WindowsError as error:
            if error.args[0] != 2:
                print(str(datetime.datetime.now()) + ": " + MODEM + ":", error, ": Обращение к модему не возможно!!!")
            return
    MODULATION = re.compile("Modulation")
    LINE_STATE = re.compile("Line State")
    LINE_STATE_TEXT = re.compile("<[^>]+>")
    SNR_MARGIN = re.compile("SNR Margin")
    DATA_RATE = re.compile("Data Rate")
    SAMPLE_LEN = 24
    SAMPLE_LEN_2 = int(SAMPLE_LEN / 2)
    get_full_info = True
    modem_state = modem_last_reboot_time = data_rate = None
    snr_list = []
    modem_last_access_time = datetime.datetime.now()
    while True:
        if modem_last_access_time is not None and datetime.datetime.now() - modem_last_access_time > datetime.timedelta(minutes=5):
            with print_lock:
                print(str(datetime.datetime.now()) + ": Нет доступа к модему...")
            speaker_queue.put(_("Modem is not accessible"))
            modem_state = modem_last_access_time = None
            get_full_info = True
        time.sleep(5)
        with reconnect_lock:
            current_modem_state, snr, current_data_rate = get_status(full_info=get_full_info)
        if current_modem_state:
            modem_last_access_time = datetime.datetime.now()
            if current_modem_state != modem_state:
                with print_lock:
                    print(str(datetime.datetime.now()) + ": Состояние ADSL линии: " + current_modem_state + "...")
                if current_modem_state == "Showtime":
                    get_full_info = False
                    if current_data_rate != data_rate:
                        with open(RATE_FILE, "a", newline=os.linesep) as f:
                            f.write(str(datetime.datetime.now()) + ": " + current_data_rate + ("" if modem_state is None else " =") + "\n")
                        data_rate = current_data_rate
                    if modem_state is not None:
                        snr_list = []
                        try:
                            os.replace(SNR_FILE, SNR_FILE+".bak")
                        except Exception:
                            pass
                        time.sleep(30)
                        if reconnect_internet_thread is not None:
                            try:
                                reconnect_internet_thread.cancel()
                            except AttributeError:
                                with print_lock:
                                    print(str(datetime.datetime.now()) + ": Ожидание отмены переподключения интернета при изменении состояния ADSL линии...")
                            reconnect_internet_thread.join()
                        online_time, ip_address, current_router_status = router_status()
                        if online_time is None or online_time == datetime.timedelta() or online_time > datetime.timedelta(seconds=45):
                            with print_lock:
                                print(str(datetime.datetime.now()) + ": Переподключение интернета при изменении состояния ADSL линии...")
                            reconnect_internet_thread = threading.Thread(target=router_status, kwargs={"reconnect": True, "force": True})
                            reconnect_internet_thread.daemon = True
                            reconnect_internet_thread.start()
                elif not get_full_info:
                    get_full_info = True
                modem_state = current_modem_state
                if modem_state == "Down":
                    time.sleep(20)
                    continue
        try:
            current_snr = float(snr)
        except ValueError:
            continue
        snr_list.append(current_snr)
        while len(snr_list) > SAMPLE_LEN:
            snr_list.pop(0)
        with open(SNR_FILE, "w", newline=os.linesep) as f:
            f.write("\n".join(map(str, snr_list)) + "\n{0:-^8}\n{1}".format(len(snr_list), sum(snr_list) / len(snr_list)))
        if len(snr_list) < SAMPLE_LEN:
            continue
        now = datetime.datetime.now()
        line_quality = sum(snr_list) / SAMPLE_LEN
        low_line_quality =  line_quality < 2.4 or (line_quality < 2.8 and sum(snr_list[:SAMPLE_LEN_2]) / SAMPLE_LEN_2 >= sum(snr_list[SAMPLE_LEN_2:]) / SAMPLE_LEN_2)
        if low_line_quality and (modem_last_reboot_time is None or now - modem_last_reboot_time > datetime.timedelta(minutes=10)):
            with print_lock:
                print(str(now) + ": Перезагрузка модема из-за низкого качества линии...")
            speaker_queue.put(_("Rebooting modem due to low line quality"))
            if get_status(reboot=True) is None:
                modem_last_reboot_time = now
                modem_state = None
                time.sleep(10)
            else:
                with print_lock:
                    print(str(datetime.datetime.now()) + ": Ошибки при перезагрузке модема...")
                speaker_queue.put(_("Errors occured while trying to reboot modem"))

def router_status(reconnect=False, force=False):
    def get_status():
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
    
    global router_credential, last_internet_connect
    now = datetime.datetime.now()
    STATUS = {0: _("disconnected"), 1: _("connected"), 2: _("connecting")}
    try:
        router_credential
    except NameError:
        with print_lock, get_reg_key() as reg_key:
            try:
                router_credential = winreg.QueryValueEx(reg_key, ROUTER)[0]
            except WindowsError as error:
                if error.args[0] != 2:
                    print(str(now) + ": " + ROUTER + ":", error, ": Обращение к роутеру не возможно!!!")
                return None
    with reconnect_lock:
        if reconnect:
            with print_lock:
                print(str(now) + ": Переподключение интернета...")
            speaker_queue.put(_("Reconnecting internet"))
        try:
            auth_handler = urllib.request.HTTPBasicAuthHandler()
            auth_handler.add_password(*itertools.chain(("TP-LINK Gigabit Broadband VPN Router R600VPN", ROUTER_ADDRESS + "/"),
                                                       pickle.loads(win32crypt.CryptUnprotectData(router_credential,
                                                                                                  bytes(__file__, "utf-8"), None, None, 0)[1])))
            opener = urllib.request.build_opener(auth_handler)
            online_time, status, ip_address = get_status()
            now = datetime.datetime.now()
            if status == 1:
                last_internet_connect = (now - online_time).replace(microsecond=0)
            if not reconnect:
                return online_time if status == 1 else None, ip_address, status
            if force or (status and (last_internet_connect is None or now > last_internet_connect + MINIMUM_WAN_CONNECT_TIME_FOR_RECONNECT)):
                opener.open(ROUTER_ADDRESS + STATUS_PAGE + WAN_DISCONNECT, timeout=10)
                opener.close()
                time.sleep(20)
                disconnected = False
                for count in range(36):
                    time.sleep(5)
                    online_time, status, ip_address = get_status()
                    if disconnected and status == 1:
                        break
                    elif status != 1:
                        disconnected = True
                    if status == 0:
                        opener.open(ROUTER_ADDRESS + STATUS_PAGE + WAN_CONNECT, timeout=10)
                        opener.close()
                else:
                    if disconnected and status != 1:
                        with print_lock:
                            print(str(datetime.datetime.now()) + ": Интернет отключен, подключение не удалось, статус: " + STATUS[status] + "...")
                        speaker_queue.put(_("Internet is disconnected, reconnection was not successfull with status: ") + STATUS[status] + "!")
                        return status
                    elif not disconnected:
                        with print_lock:
                            print(str(datetime.datetime.now()) + ": Интернет не отключен, статус: " + STATUS[status] + "...")
                        speaker_queue.put(_("Internet is not disconnected, current status: ") + STATUS[status] + "!")
                        return status
                with print_lock:
                    print(str(datetime.datetime.now()) + ": Успешное переподключение интернета...")
                speaker_queue.put(_("Internet reconnected successfully"))
                return status
            else:
                with print_lock:
                    print(str(datetime.datetime.now()) + ": Переподключение не выполнено: " +
                          ("интернет не был подключен, выполни подключение вручную!!!" if not status
                           else "слишком малый промежуток с момента предыдущего подключения..."))
                speaker_queue.put(_("Internet reconnection denied by script policy"))
        except urllib.error.URLError as error:
            match = WIN_ERROR.search(str(error))
            if not (isinstance(error.reason, socket.timeout) or (match is not None and int(match.group(1)) in (10054, 10060, 10065))):
                str_error = str(error)
        except WindowsError as error:
            if not (isinstance(error, socket.timeout) or error.args[0] in (10054, 10060, 10065)):
                str_error = "w" + str(error)
        except Exception:
            str_error = str(sys.exc_info()[0]) + " (" + str(sys.exc_info()[1]) + ")"
        finally:
            opener.close()
        try:
            with print_lock:
                print(str(datetime.datetime.now()) + ": Ошибка при обращении к роутеру: " + str_error)
            speaker_queue.put(_("An error occurred while trying to ") + (_("reconnect internet") if reconnect else _("get status info")))
        except NameError:
            pass
        return None if reconnect else (None, None, None)


def print_ip_address(prev_ip_address):
    global reconnect_internet_thread
    prev_online_time = datetime.timedelta()
    while True:
        online_time, ip_address, current_router_status = router_status()
        now = datetime.datetime.now()
        if online_time is not None:
            if reconnect_internet_thread is not None:
                try:
                    reconnect_internet_thread.cancel()
                except AttributeError:
                    pass
                reconnect_internet_thread.join()
                reconnect_internet_thread = None
            ip_address = (status if status is not None else "") + ip_address
            message_tail = "IP адрес: " + ip_address.lstrip("+-") + "\n" + " " * 17 + "подключен: " + str(last_internet_connect)
            if prev_ip_address != ip_address:
                if status != "-":
                    with print_lock:
                        print(str(datetime.datetime.now()) + ": " + ("Новый " if last_internet_connect > start_time else "") + message_tail)
                if status is not None:
                    time.sleep(10)
                    update_dyndns_address_thread = threading.Thread(target=update_dyndns_address, args=(ip_address, ))
                    update_dyndns_address_thread.daemon = True
                    update_dyndns_address_thread.start()
                    time.sleep(50)
                prev_ip_address = ip_address  # prev_ip_address - локальный
            elif online_time < prev_online_time:
                with print_lock:
                    print(str(datetime.datetime.now()) + ": Тот же " + message_tail)
            prev_online_time = online_time
        elif current_router_status == 0 and reconnect_internet_thread is not None:
            try:
                reconnect_internet_thread.cancel()
            except AttributeError:
                with reconnect_lock:
                    continue
            reconnect_internet_thread.join()
            reconnect_internet_thread = None
        elif current_router_status == 2 and (reconnect_internet_thread is None or not reconnect_internet_thread.is_alive()):
            reconnect_internet_thread = threading.Timer(90, router_status, kwargs={"reconnect": True})
            reconnect_internet_thread.daemon = True
            reconnect_internet_thread.start()
        time.sleep(20)


def idna(s):
    "Преобразует список адресов хостов в punycode"
    return ",".join(map(lambda x: x.encode("idna").decode("iso-8859-1"), s.split(",")))


def update_dyndns_address(status_and_new_address):
    def get_ip_address():
        online_time, ip_address, current_router_status = router_status()
        if online_time is not None:
            return status + ip_address
        return None

    global prev_ip_address
    offline = status_and_new_address.startswith("-")
    new_address = status_and_new_address[1:]
    regexp_tail = r"\r?\n?){{{}}}$".format(len(DYNDNS_HOST_NAMES.split(",")))
    DYNDNS_CLIENT_VERSION = "Konstantin Kulakov-Monitor2.py/2.03"  # Версия 2: переход на urllib.request и получение ip с роутера
    NEXT_UPDATE_TIME = "NextUpdate"
    NEXT_UPDATE_MSG = "    Следующая попытка обновления через "
    ERROR_MSG = ": Ошибка {0}при обновлении DynDNS: "
    off = " (перевод в offline)" if offline else ""
    ver = DYNDNS_CLIENT_VERSION.split("/")[1]
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(capath=os.path.dirname(__file__))
    ssl_handler = urllib.request.HTTPSHandler(context=context)
    auth_handler = urllib.request.HTTPBasicAuthHandler()
    auth_handler.add_password(*itertools.chain(("DynDNS API Access", DYNDNS_MEMBERS + "/"),
                                               pickle.loads(win32crypt.CryptUnprotectData(dyndns_data,
                                                                                          bytes(__file__, "utf-8"), None, None, 0)[1])))
    opener = urllib.request.build_opener(ssl_handler, auth_handler)
    opener.addheaders = [("User-Agent", DYNDNS_CLIENT_VERSION)]
    while True:
        with print_lock, get_reg_key() as reg_key:
            next_updat_time = get_time_from_reg(reg_key, NEXT_UPDATE_TIME)
        now = datetime.datetime.now()
        if next_updat_time is not None and next_updat_time > now + datetime.timedelta(seconds=1):
            with print_lock:
                print(str(now) + ": Ожидание начала обновления DynDNS до " + str(next_updat_time) + "...")
            time.sleep((next_updat_time-now).total_seconds())
        ip_address = get_ip_address()
        if ip_address is None or ip_address != status_and_new_address or os.path.exists(DYNDNS_UPDATE_ERROR_FILE):
            with print_lock:
                print(str(datetime.datetime.now()) + ": " + new_address + off + ": Отмена обновления DynDNS...")
            return
        try:
            with print_lock:
                print(str(datetime.datetime.now()) + ": " + new_address + off + ": Выполняется обновление DynDNS/" + ver + "...")
            response = opener.open(DYNDNS_MEMBERS + "/nic/update?hostname=" + DYNDNS_HOST_NAMES + "&myip=" + new_address +
                                   ("&offline=yes" if offline else ""), timeout=20)
        except socket.error as error:
            with print_lock, get_reg_key(access=winreg.KEY_ALL_ACCESS) as reg_key:
                print(str(datetime.datetime.now()) + ": " + new_address + off + ERROR_MSG.format("") + str(error))
                print(NEXT_UPDATE_MSG + str(DYNDNS_UPDATE_INTERVAL[0]) + " " + DYNDNS_UPDATE_INTERVAL[1] + "...")
                update_time_in_reg(reg_key, NEXT_UPDATE_TIME, datetime.datetime.now()+datetime.timedelta(minutes=DYNDNS_UPDATE_INTERVAL[0]))
            time.sleep(DYNDNS_UPDATE_INTERVAL[0]*60)
            continue
        except ssl.SSLError as error:
            with print_lock, open(DYNDNS_UPDATE_ERROR_FILE, "a") as err_file:
                print(str(datetime.datetime.now()) + ": " + new_address + off + ERROR_MSG.format("SSL ") + str(error))
                err_file.write(str(datetime.datetime.now()) + ": " + status_and_new_address + ": SSLError: " +
                               str(error) + "\n")
            return
        finally:
            opener.close()
        return_code = str(response.read(), "iso-8859-1", "replace")
        match = re.match(r"(dnserr|911)$", return_code)
        if match is not None:
            with print_lock, get_reg_key(access=winreg.KEY_ALL_ACCESS) as reg_key:
                print(str(datetime.datetime.now()) + ": " + new_address + off + ERROR_MSG.format("на сервере Dyn ") + match.group(1))
                print(NEXT_UPDATE_MSG + str(DYNDNS_UPDATE_INTERVAL2[0]) + " " + DYNDNS_UPDATE_INTERVAL2[1] + "...")
                update_time_in_reg(reg_key, NEXT_UPDATE_TIME, datetime.datetime.now()+datetime.timedelta(minutes=DYNDNS_UPDATE_INTERVAL2[0]))
            time.sleep(DYNDNS_UPDATE_INTERVAL2[0]*60)
            continue
        elif re.match("(?:good " + re.escape(new_address) + regexp_tail, return_code) is None:
            str_now = str(datetime.datetime.now())
            with print_lock, open(DYNDNS_UPDATE_ERROR_FILE, "a") as err_file:
                print(str_now + ": " + new_address + off + ": Код возврата DynDNS: " + return_code + " (status: " + str(response.status) + ")")
                err_file.write(str_now + ": " + return_code + " (status: " + str(response.status) + ")\n")
            return
        break
    with print_lock, get_reg_key(access=winreg.KEY_ALL_ACCESS) as reg_key:
        print(str(datetime.datetime.now()) + ": " + new_address + off + ": Успешное обновление DynDNS...")
        prev_ip_address = status_and_new_address
        try:
            winreg.SetValueEx(reg_key, DYNDNS_IP_ADDRESS, 0, winreg.REG_SZ, status_and_new_address)
        except WindowsError as error:
            print(DYNDNS_IP_ADDRESS + ":", error, "!!!")
            with open(DYNDNS_UPDATE_ERROR_FILE, "a") as err_file:
                err_file.write(str(datetime.datetime.now()) + ": " + status_and_new_address + ": Registry: " + str(error) + "\n")


def shutdown_nas():
    RESPONCE = '{"http_code":200}'
    now = datetime.datetime.now()
    try:
        response = urllib.request.urlopen("http://" + NAS_ADDRESS + SHUTDOWN_LOCATION, timeout=30)
        response_text = str(response.read(), "iso-8859-1", "replace")
        if re.search(RESPONCE, response_text):
            with print_lock:
                print(str(datetime.datetime.now()) + ": NAS начал выключение...")
            return
        else:
            with print_lock:
                print(str(datetime.datetime.now()) + ": NAS не начал выключение (ответ: " +
                response_text + ")!!!")
    except Exception as error:
        with print_lock:
            print(str(datetime.datetime.now()) + ": Ошибка при выключении NAS: " + str(error))


def manage_vm():
    def process_window(handle, close=False, hwnd_tuple=None):
        def callback(hwnd, param):
            nonlocal result
            if close:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            elif isinstance(hwnd_tuple, tuple):
                result |= hwnd in hwnd_tuple
        try:
            thread_handles = list(map(lambda x: int(x.Handle), wmi.ExecQuery(QUERY2.format(handle), "WQL", 48)))
        except Exception:
            return
        result = False
        for thread_handle in thread_handles:
            try:
                win32gui.EnumThreadWindows(thread_handle, callback, 0)
            except Exception:
                pass
        return result

    def must_warn(handle):
        return process_window(handle, hwnd_tuple=(win32gui.GetForegroundWindow(), win32gui.GetActiveWindow()))

    def shutdown_vm(handle):
        process_window(handle, close=True)

    def record_time(item, test_date, test_time, is_future=False):
        '''record_time(item, test_date, test_time)
        Возвращает булево, указывающее, выполняется или нет запланированная запись Behold TV,
        Если запись была снята и время записи закончилось, устанавливает флаг reset_config[schedule_file_no]'''
        if item[1] <= item[2]:
            result = (((not item[3] and test_date == item[0]) or (item[3] and pow(2, test_date.isoweekday()-1) & item[3]))
                      and item[1] <= test_time <= item[2])
        else:
            prev_date = test_date - datetime.timedelta(days=1)
            result = ((((not item[3] and test_date == item[0]) or (item[3] and pow(2, test_date.isoweekday()-1) & item[3]))
                       and item[1] <= test_time)
                      or (((not item[3] and prev_date == item[0]) or (item[3] and pow(2, prev_date.isoweekday()-1) & item[3]))
                          and test_time <= item[2]))
        if item[4]:
            if result:
                result = False
            elif not is_future:
                reset_config[item[5]] = True
        return result

    def forbidden(now):
        def is_forbidden(test_datetime, is_future):
            nonlocal close_browsers
            test_date = test_datetime.date()
            test_time = test_datetime.time()
            if test_time < VM_START_TIME or test_time >= VM_STOP_TIME:
                return True
            for item in schedule_list:
                if record_time(item, test_date, test_time, is_future):
                    close_browsers = True
                    return True
            return False

        nonlocal vm_started_time
        close_browsers = False
        if shutdown_vm_flag or os.path.exists(VM_FLAG_FILE):
            vm_started_time = None
            return True, True, -1, False
        to_run = to_start = warning = False
        for i in range(max(WARNING_TIME, MIN_VM_START_TIME_BEFORE_STOP)+1):
            if is_forbidden(now+datetime.timedelta(minutes=i), i):
                if i <= MEMORY_FREE_TIME:
                    to_run = True
                if i <= WARNING_TIME:
                    warning = i - MEMORY_FREE_TIME
                if i <= MIN_VM_START_TIME_BEFORE_STOP:
                    to_start = True
                break
        return to_run, to_start, warning, close_browsers if to_run else False

    def get_datetime_from_output(bytes_datetime):
        return datetime.datetime.strptime(str(bytes_datetime, encoding="utf-8").strip(), "%Y-%m-%d %H:%M:%S")

    pythoncom.CoInitialize()
    global schedule_list
    MEMORY_FREE_TIME = 5
    WARNING_TIME = MEMORY_FREE_TIME + 10
    MIN_VM_RUN_TIME = 10
    MIN_VM_START_TIME_BEFORE_STOP = MIN_VM_RUN_TIME + MEMORY_FREE_TIME + 1
    VM_PLAYER = "vmplayer.exe"
    MESSAGE_HEAD = _("virtual machine will be turned off after ")
    ENCODING = "windows-1251"
    BEHOLDTV_FOLDER = os.path.join(os.getenv('homedrive'), os.getenv('homepath'), r"AppData\Roaming\BeholdTV")
    SCHEDULE_FILES = [os.path.join(BEHOLDTV_FOLDER, "Schedule.ini")]
    try:
        with open(START_VM_CMD_FILE, encoding='cp866') as f:
            match = re.search(r'"[^"]+{0}"\s+("[^"]+\.vmx")'.format(re.escape(VM_PLAYER)) , f.read())
            if match is None:
                raise Exception
        vmx = match.group(1)
        last_modified = os.stat(START_VM_CMD_FILE).st_mtime
    except Exception:
        with print_lock:
            print(str(datetime.datetime.now()) + ': vm: Отсутствует или не распознан скрипт запуска виртуальной машины: "' + START_VM_CMD_FILE + '"...')
            print("    Управление виртуальной машиной производиться не будет...")
        return
    QUERY1 = "Select Handle from Win32_Process where name='{0}' and CommandLine like '%{1}%'".format(VM_PLAYER, vmx.replace('\\', '\\\\'))
    QUERY2 = "Select Handle from Win32_Thread where ProcessHandle='{0}'"
    QUERY3 = full_path("powershell") + ''' "(Get-WinEvent -ErrorAction SilentlyContinue -LogName 'System' -MaxEvents 1 -FilterXPath '* [ System [ Provider[@Name="""{0}"""] and EventID{1} ] ]').TimeCreated.ToString('u').Trim('Z')"'''

    try:
        system_start_time = get_datetime_from_output(subprocess.check_output(QUERY3.format('EventLog' ,'[@Qualifiers=32768]=6009')))
    except Exception:
        system_start_time = None
    try:
        system_quick_start_time = get_datetime_from_output(subprocess.check_output(QUERY3.format('Microsoft-Windows-Power-Troubleshooter' ,'=1')))
    except Exception:
        system_quick_start_time = None
    if system_start_time is None and system_quick_start_time is None:
        with print_lock:
            print(str(datetime.datetime.now()) + ": vm: Ошибка при попытке определения времени старта системы...")
            print("    Старт системы будет считаться от старта скрипта...")
        vm_start_time = start_time + datetime.timedelta(minutes=30)
    elif system_quick_start_time is not None and (system_start_time is None or system_quick_start_time > system_start_time):
        vm_start_time = system_quick_start_time + datetime.timedelta(minutes=15)
    else:
        vm_start_time = system_start_time + datetime.timedelta(minutes=30)
    min_start_time = datetime.datetime.combine(datetime.date.today(), VM_START_TIME)
    if vm_start_time < min_start_time:
        vm_start_time = min_start_time
    vm_started_time = vm_handle  = schedule_list = None
    instance_list = [[] for x in range(len(SCHEDULE_FILES))]
    reset_config = [False for x in range(len(SCHEDULE_FILES))]
    schedule_file_last_modified = [None for x in range(len(SCHEDULE_FILES))]
    was_warned = -1
    change_completed = True
    wmi = win32com.client.GetObject(MONIKER)
    while True:
        time.sleep(5)
        completed_count = 0
        for schedule_file_no in range(len(SCHEDULE_FILES)):
            schedule_file = SCHEDULE_FILES[schedule_file_no]
            try:
                st_mtime = os.stat(schedule_file).st_mtime
            except FileNotFoundError:
                st_mtime = None
            if reset_config[schedule_file_no] or schedule_file_last_modified[schedule_file_no] != st_mtime:
                reset_config[schedule_file_no] = False
                schedule_list = None
                for i in range(6):
                    try:
                        instance_list[schedule_file_no] = []
                        write_changed = False
                        config = configparser.ConfigParser()
                        config.optionxform = lambda option: option
                        st_mtime = os.stat(schedule_file).st_mtime
                        with open(schedule_file, encoding=ENCODING) as f:
                            config.read_file(f)
                        now = datetime.datetime.now()
                        test_date = now.date()
                        test_time = now.time()
                        for section in config.sections():
                            if section.startswith("Job"):
                                if config[section]["JobEnable"] + config[section]["JobModeCap"] == "10":
                                    item = [datetime.datetime.strptime(config[section]["JobDate"], "%d.%m.%Y").date(),
                                            datetime.datetime.strptime(config[section]["JobStart"], "%H:%M:%S").time(),
                                            datetime.datetime.strptime(config[section]["JobStop"], "%H:%M:%S").time(),
                                            int(config[section]["JobDays"]), int(config[section]["JobCancel"]), schedule_file_no]
                                    record_time(item, test_date, test_time)  # Проверим не завершилось ли время записи снятой задачи
                                    if reset_config[schedule_file_no]:
                                        config[section]["JobCancel"] = "0"
                                        reset_config[schedule_file_no] = False
                                        write_changed = True
                                    instance_list[schedule_file_no].append(item)
                        if st_mtime != os.stat(schedule_file).st_mtime:
                            raise Exception
                        if write_changed:
                            os.replace(schedule_file, schedule_file + ".bak")
                            with open(schedule_file, "w", encoding=ENCODING, newline="\r\n") as f:
                                config.write(f, space_around_delimiters=False)
                            raise Exception
                        completed_count += 1
                        schedule_file_last_modified[schedule_file_no] = st_mtime
                        break
                    except Exception:
                        time.sleep(5)
                else:
                    completed_count += 1
                    with print_lock:
                        print(str(now) + ": vm: Не удалось обновить информацию из планировщика BeholdTV...")
                        print("    Запланированные записи экземпляра {0} не будут отслеживаться...".format(schedule_file_no))
                was_warned = -1
                del config, section
            else:
                completed_count += 1
        if completed_count != len(SCHEDULE_FILES):
            continue
        if schedule_list is None:
            temp_list = []
            for i in range(len(instance_list)):
                temp_list.extend(instance_list[i])
            schedule_list = temp_list
            del temp_list
            time.sleep(30)
        try:
            if last_modified != os.stat(START_VM_CMD_FILE).st_mtime:
                with print_lock:
                    print(str(now) + ": vm: Изменен скрипт запуска виртуальной машины...")
                    print("    Выполняется выключене машины и перезапуск менеджера...")
                shutdown_vm(vm_handle)
                manage_vm_thread = threading.Thread(target=manage_vm)
                manage_vm_thread.daemon = True
                manage_vm_thread.start()
                return
        except Exception:
            pass
        now = datetime.datetime.now()
        if vm_handle is None:
            try:
                vm_handle = list(map(lambda x: x.Handle, wmi.ExecQuery(QUERY1, "WQL", 48)))[0]
                with print_lock:
                    print(str(now) + ": vm: Виртуальная машина работает...")
                change_completed = True
                was_warned = -1
                continue
            except Exception:
                pass
            if change_completed and not forbidden(now)[1] and now > vm_start_time:
                with print_lock:
                    print(str(now) + ": vm: Выполняется запуск виртуальной машины...")
                speaker_queue.put(_("virtual machine is turning on"))
                subprocess.call('"' + COMSPEC + '" /c "' + START_VM_CMD_FILE + '"')
                vm_started_time = now
                change_completed = False
        else:
            try:
                win32com.client.GetObject(MONIKER + ":Win32_Process.Handle=" + vm_handle)
            except Exception:
                vm_handle = None
                with print_lock:
                    print(str(now) + ": vm: Виртуальная машина не работает...")
                change_completed = True
                continue
            is_forbidden = forbidden(now)
            if was_warned != is_forbidden[2]:
                was_warned = is_forbidden[2]
                if was_warned > 0 and must_warn(vm_handle):
                    if was_warned == 1:
                        speaker_queue.put(MESSAGE_HEAD + _("1 minute"))
                    elif 2 <= was_warned < 5:
                        speaker_queue.put(MESSAGE_HEAD + _("{0} minutes").format(was_warned))
                    else:
                        speaker_queue.put(MESSAGE_HEAD + _("{0} minutes.").format(was_warned))
            if change_completed and is_forbidden[0] and (vm_started_time is None or now > vm_started_time + datetime.timedelta(minutes=MIN_VM_RUN_TIME)):
                with print_lock:
                    print(str(now) + ": vm: Выполняется остановка виртуальной машины...")
                speaker_queue.put(_("virtual machine is turning off"))
                shutdown_vm(vm_handle)
                if is_forbidden[3]:
                    close_browsers_thread = threading.Timer(30, close_browsers)
                    close_browsers_thread.daemon = True
                    close_browsers_thread.start()
                change_completed = False


def close_browsers():
    for pid in psutil.get_pid_list():
        try:
            if psutil.Process(pid).name != "chrome.exe":
                continue
        except Exception:
            continue
        os.startfile("http://")
        time.sleep(5)
        break
    for browser in ("chrome", "firefox", "iexplore"):
        call_("taskkill /im {0}.exe".format(browser))


def nas_check_time_process():
    delta = datetime.datetime.combine(datetime.date.today(), NAS_CHECK_TIME_AFTER) - datetime.datetime.now()
    if delta > datetime.timedelta():
        time.sleep(delta.total_seconds())
    while True:
        nas_check_time = None
        if os.path.exists(NAS_CHECK_TIME_FILE):
            try:
                with open(NAS_CHECK_TIME_FILE) as f:
                    nas_check_time = datetime.datetime.strptime(f.read(), "%Y-%m-%dT%H:%M:%S")
            except Exception:
                pass
        now = datetime.datetime.now()
        try:
            if nas_check_time is None or nas_check_time.date() != now.date():
                nas_check_time = now.replace(microsecond=0)
                with open(NAS_CHECK_TIME_FILE, "w") as f:
                    f.write(str(now.isoformat()[:19]))
            mtime = datetime.datetime.fromtimestamp(os.stat(NAS_CHECK_TIME_FILE).st_mtime).replace(microsecond=0)
            if abs(nas_check_time - mtime) > datetime.timedelta(minutes=5):
                with print_lock:
                    print(str(now) + ": NAS не синхронизирован...")
                speaker_queue.put(_("Check NAS synchronization"))
        except Exception:
            with print_lock:
                print(str(now) + ": NAS не подключен...")
            speaker_queue.put(_("NAS is not connected"))
        delta = now - datetime.datetime.combine(datetime.date.today(), NAS_CHECK_TIME_AFTER)
        time.sleep((datetime.timedelta(days=1) - delta).total_seconds())


def process_events():
    global status, shutdown_vm_flag
    SECTION_WEEKDAY = re.compile("WeekDay([1-7])$")
    SHUTDOWN_TIME = "Shutdown"
    HYBRID_SHUTDOWN = "HybridShutdown"
    MAX_BEFORE_RESUME_SHUTDOWN_TIME = (datetime.datetime.combine(datetime.date.today(), RESUME_TIME) -
                                       datetime.timedelta(minutes=MIN_OFFLINE_TIME)).time()
    MIN_AFTER_RESUME_SHUTDOWN_TIME = (datetime.datetime.combine(datetime.date.today(), RESUME_TIME) +
                                      datetime.timedelta(minutes=MIN_ONLINE_TIME)).time()
    last_modified = None
    while True:
        try:
            st_mtime = os.stat(INI_FILE).st_mtime
        except FileNotFoundError:
            st_mtime = None
        if last_modified != st_mtime:
            shutdown_dict = {}
            config = configparser.ConfigParser()
            config.optionxform = lambda option: option
            try:
                with open(INI_FILE, encoding="utf-8-sig") as f:
                    config.read_file(f)
            except FileNotFoundError:
                st_mtime = None
            except Exception as error:
                with print_lock:
                    print(str(datetime.datetime.now()) + ": ошибки при считыавнии ini-файла: " + str(error))
                    print("    Используются предопределенные значения...")
            try:
                default_shutdown_time = datetime.datetime.strptime(config['DEFAULT'][SHUTDOWN_TIME], "%H:%M").time()
            except KeyError:
                default_shutdown_time = datetime.time(22, 30)
            try:
                default_mode = int(config['DEFAULT'][HYBRID_SHUTDOWN])
            except KeyError:
                default_mode = 0

            for i in range(7):
                shutdown_dict.setdefault(i+1, [default_shutdown_time, default_mode])
            for section in config.sections():
                match = SECTION_WEEKDAY.match(section)
                if match is not None:
                    weekday = int(match.group(1))
                    try:
                        shutdown_dict[weekday][0] = datetime.datetime.strptime(config[section][SHUTDOWN_TIME], "%H:%M").time()
                    except KeyError:
                        pass
                    try:
                        shutdown_dict[weekday][1] = int(config[section][HYBRID_SHUTDOWN])
                    except KeyError:
                        pass
            try:
                if st_mtime is not None and st_mtime != os.stat(INI_FILE).st_mtime:
                    raise FileNotFoundError
            except FileNotFoundError:
                time.sleep(1)
                continue
            last_modified = st_mtime
            del config, section

        now = datetime.datetime.now().replace(second=0, microsecond=0)
        today = now.date()
        shutdown_today = True
        without_resume = False
        if now.time() >= RESUME_TIME:
            shutdown_event = shutdown_dict[today.isoweekday()]
            if shutdown_event[0] < RESUME_TIME:
                shutdown_today = False
        else:
            try:
                shutdown_event = shutdown_dict[today.isoweekday()-1]
            except KeyError:
                shutdown_event = shutdown_dict[7]
        for i in range(30):
            try:
                if isinstance(schedule_list, list):
                    for item in schedule_list:
                        if now.time() >= RESUME_TIME:
                            if shutdown_today:
                                if (not item[3] and today == item[0]) or (item[3] and pow(2, today.isoweekday()-1) & item[3]):
                                    if item[1] <= item[2]:
                                        if shutdown_event[0] < item[2]:
                                            shutdown_event[0] = item[2]
                                    else:
                                        shutdown_today = False
                                else:
                                    next_date = today + datetime.timedelta(days=1)
                                    if (((not item[3] and next_date == item[0]) or (item[3] and pow(2, next_date.isoweekday()-1) & item[3]))
                                        and item[1] < RESUME_TIME):
                                        shutdown_today = False
                        elif not without_resume:
                            if item[1] <= item[2]:
                                if (((not item[3] and today == item[0]) or (item[3] and pow(2, today.isoweekday()-1) & item[3]))
                                    and item[1] < RESUME_TIME and (shutdown_event[0] > RESUME_TIME or shutdown_event[0] < item[2])):
                                    if item[2] > MAX_BEFORE_RESUME_SHUTDOWN_TIME:
                                        without_resume = True
                                    else:
                                        shutdown_event[0] = item[2]
                            else:
                                prev_date = today - datetime.timedelta(days=1)
                                if (((not item[3] and prev_date == item[0]) or (item[3] and pow(2, prev_date.isoweekday()-1) & item[3]))
                                    and (shutdown_event[0] > RESUME_TIME or shutdown_event[0] < item[2])):
                                    if item[2] > MAX_BEFORE_RESUME_SHUTDOWN_TIME:
                                        without_resume = True
                                    else:
                                        shutdown_event[0] = item[2]
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            with print_lock:
                print(str(datetime.datetime.now()) +": Не удалось обработать данные, полученные из планировщика BeholdTV...")
                print('    Будут выполняться только запланированные в "{0}" выключения компьютера...'.format(os.path.basename(INI_FILE)))
        if ((not (MAX_BEFORE_RESUME_SHUTDOWN_TIME < now.time() <= MIN_AFTER_RESUME_SHUTDOWN_TIME))
            and shutdown_today and not without_resume and datetime.datetime.combine(today, shutdown_event[0]) == now):
            with print_lock:
                print(str(datetime.datetime.now()) +": Началось запланированние выключение компьютера...")
            speaker_queue.put(_("Planned shutdown started"))
            if not STATIC_ADDRESS and status == "+":
                status = "-"
            shutdown_vm_flag = True
            subprocess.Popen(full_path('shutdown.exe') +
                             ' /s {0}/t 90 /d p:0:0 /c "Запланированное выключение компьютера"'.format('/hybrid ' if shutdown_event[1] else ''))
            for pid in psutil.get_pid_list():
                try:
                    if psutil.Process(pid).name != "WWAHost.exe":
                        continue
                except Exception:
                    continue
                os.startfile("skype:")
                time.sleep(5)
                call_("taskkill /im wwahost.exe")
                break
            close_browsers()
        time.sleep(max(0, (now.replace(second=5) + datetime.timedelta(minutes=1) - datetime.datetime.now()).total_seconds()))


def process_ini():
    VM_START_TIME = "VMStartTime"
    VM_STOP_TIME = "VMStopTime"
    SPEAKER_START_TIME = "SpeakerStartTime"
    SPEAKER_STOP_TIME = "SpeakerStopTime"
    RESUME_TIME = "ResumeTime"
    MIN_OFFLINE_TIME = "MinOfflineTime"
    config = configparser.ConfigParser()
    config.optionxform = lambda option: option
    try:
        with open(INI_FILE, encoding="utf-8-sig") as f:
            config.read_file(f)
    except Exception:
        return None, None, None

    try:
        start_time = datetime.datetime.strptime(config['DEFAULT'][VM_START_TIME], "%H:%M").time()
    except KeyError:
        start_time = None
    try:
        stop_time = datetime.datetime.strptime(config['DEFAULT'][VM_STOP_TIME], "%H:%M").time()
    except KeyError:
        stop_time = None
    vm_settings = (start_time, stop_time) if start_time is not None or stop_time is not None else None

    try:
        start_time = datetime.datetime.strptime(config['DEFAULT'][SPEAKER_START_TIME], "%H:%M").time()
    except KeyError:
        start_time = None
    try:
        stop_time = datetime.datetime.strptime(config['DEFAULT'][SPEAKER_STOP_TIME], "%H:%M").time()
    except KeyError:
        stop_time = None
    speaker_settings  = (start_time, stop_time) if start_time is not None or stop_time is not None else None

    try:
        resume_time = datetime.datetime.strptime(config['DEFAULT'][RESUME_TIME], "%H:%M").time()
    except KeyError:
        resume_time = None
    try:
        min_offline_time = int(config['DEFAULT'][MIN_OFFLINE_TIME])
    except KeyError:
        min_offline_time = None
    return (vm_settings, speaker_settings, resume_time, min_offline_time)


if __name__ == "__main__":
    SCRIPT_NAME = os.path.splitext(__file__)[0]
    INI_FILE = SCRIPT_NAME + ".ini"
    SNR_FILE = SCRIPT_NAME + ".snr"
    RATE_FILE = SCRIPT_NAME + ".dat"
    INI_VM_SETTINGS, INI_SPEAKER_SETTINGS, RESUME_TIME, MIN_OFFLINE_TIME = process_ini()
    MONIKER = r"winmgmts:{impersonationLevel=impersonate}!\\.\root\cimv2"
    START_SCRIPT = '"' + sys.executable + '" "' + __file__ + '"'
    FIRST_LOG_LINE = "\n{0:=^65}".format("")
    WIN_ERROR = re.compile(r"\[WinError (\d+)\]")

    # Каждые UPS_TEST_PERIOD проверяется наличие запущеных служб ИБП Иппон
    UPS_TEST_PERIOD = 30  # seconds
    UPS_SIGNAL_LAG = 3  # times

    # Доступ к базе сайта
    DB_NAME = "site"
    DB_UPDATE_INTERVAL = 5  # minutes

    # Флаги отключения
    SHUTDOWN_FLAG = SCRIPT_NAME + ".shutdown"

    # Параметры, используемые клиентом DynDNS
    # http://www.dyndns.com/developers/routers/hints.html
    DYNDNS_MEMBERS = "https://members.dyndns.org"
    DYNDNS_UPDATE_INTERVAL = 10, "минут"  # Ожидание перед повтором попытки обновления адреса при отсутствии ответа сервера
    DYNDNS_UPDATE_INTERVAL2 = 30, "минут"  # Ожидание в случаях проблем на серверах Dyn
    DYNDNS_UPDATE_ERROR_FILE = SCRIPT_NAME + ".err"
    DYNDNS_DATA = "Data"
    DYNDNS_IP_ADDRESS = "IP Address"  # Имя параметра реестра для последнего удачно обновленного IP адреса
    DYNDNS_HOST_NAMES = "Host Names"
    STATIC_ADDRESS = False

    # Доступ к роутеру
    ROUTER = "Data2"
    ROUTER_ADDRESS = "http://192.168.0.1:8008"
    STATUS_PAGE = "/userRpm/StatusRpm.htm"
    STATUS_WAN_IP_ADDRESS = 7
    STATUS_ONLINE_TIME = 12
    STATUS_WAN_CONNECTED = 13
    WAN_DISCONNECT = "?Disconnect=Disconnect&wan=1"
    WAN_CONNECT = "?Connect=Connect&wan=1"
    MINIMUM_WAN_CONNECT_TIME_FOR_RECONNECT = datetime.timedelta(minutes=10)
    WAIT_FOR_RECONNECT = 900  # seconds

    # Доступ к модему
    MODEM = "Data3"
    MODEM_ADDRESS = "http://192.168.1.24"
    MODEM_STATUS_PAGE = "/status_deviceinfo.htm"
    MODEM_REBOOT_PAGE = "/Forms/tools_system_1"

    # Управление виртуальной машиной
    START_VM_CMD_FILE = os.path.join(os.path.dirname(__file__), "suse_start.cmd")
    VM_FLAG_FILE = SCRIPT_NAME + ".stop_vm"  # При наличии флага виртуальная машина выключается, в противном случае включается
    if INI_VM_SETTINGS is not None:
        VM_START_TIME, VM_STOP_TIME = INI_VM_SETTINGS
    try:
        if VM_START_TIME is None:
            raise NameError
    except NameError:
        VM_START_TIME = datetime.time(7, 10)
    try:
        if VM_STOP_TIME is None:
            raise NameError
    except NameError:
        VM_STOP_TIME = datetime.time(20, 15)

    # Время, начиная со старта отключения VM, в течение которого не проверяется свежесть данных об измерении напряжения
    VM_SHUTDOWN_DELAY = 3  # минуты, на 1 минуту больше, чем время, указанное в параметре "Максимальное время закрытия файла" Winpower агента

    # Доступ к NAS
    NAS_ADDRESS = "mybooklive"
    SHUTDOWN_LOCATION = "/UI/device/shutdown"
    NAS_CHECK_TIME_FILE = r"\\mybooklive\Public\.check_time"
    NAS_CHECK_TIME_AFTER = (datetime.datetime.combine(datetime.date.today(), VM_START_TIME) + datetime.timedelta(minutes=18)).time()

    # Управление плановыми выключениями
    if RESUME_TIME is None:
        RESUME_TIME = datetime.time(6, 30)
    if MIN_OFFLINE_TIME is None:
        MIN_OFFLINE_TIME = 8  # Минимальное время то момента старта выключения до автоматического включения, минуты
    MIN_ONLINE_TIME = 30  # Время после автоматического включения, в течение которого не производится выключение, минуты

    # Время для голосовых сообщений
    if INI_SPEAKER_SETTINGS is not None:
        SPEAKER_START_TIME, SPEAKER_STOP_TIME = INI_SPEAKER_SETTINGS
    try:
        if SPEAKER_START_TIME is None:
            raise NameError
    except NameError:
        SPEAKER_START_TIME = datetime.time(6, 30)
    try:
        if SPEAKER_STOP_TIME is None:
            raise NameError
    except NameError:
        SPEAKER_STOP_TIME = datetime.time(21)
    
    start_time = datetime.datetime.now()
    
    if len(sys.argv) == 2:
        match = re.match(r"setdata(\d?)", sys.argv[1])
        if match is not None:
            index = match.group(1)
            data = MODEM if index == "3" else ROUTER if index == "2" else DYNDNS_DATA if not index else None
            if data is not None:
                with get_reg_key(access=winreg.KEY_ALL_ACCESS) as reg_key:
                    try:
                        winreg.DeleteValue(reg_key, data)
                    except WindowsError as error:
                        if error.args[0] != 2:
                            print(data + "(Delete):", error, "!!!")
                print("User: ", end="")
                sys.stdout.flush()
                username = sys.stdin.readline().strip()
                password = getpass.getpass()
                with get_reg_key(access=winreg.KEY_ALL_ACCESS) as reg_key:
                    try:
                        winreg.SetValueEx(reg_key, data, 0, winreg.REG_BINARY,
                                          win32crypt.CryptProtectData(pickle.dumps((username, password)),
                                                                      "", bytes(__file__, "utf-8"), None, None, 0))
                    except WindowsError as error:
                        print(data + ":", error, "!!!")
            sys.exit()
    
    keep_output = False
    COMSPEC = os.getenv("comspec")
    if COMSPEC:  # Проверим на запуск в режиме сохраниеия вывода после завершения
        parent_process_moniker = (MONIKER + ":Win32_Process.Handle=" + str(os.getppid()))
        try:
            for i in range(2):
                parent_process = win32com.client.GetObject(parent_process_moniker)
                keep_output += re.match('("?)' + COMSPEC.replace("\\", r"\\").replace(".", "\\.") + '\\1\s+/[ck]\s+',
                    parent_process.CommandLine, re.IGNORECASE) is not None
                parent_process_moniker = (MONIKER + ":Win32_Process.Handle=" + str(parent_process.ParentProcessId))
        except Exception:
            pass
        finally:
            parent_process = None
    if len(sys.argv) == 2 and sys.argv[1] == "reconnect":
        reconnect = keep_output = True
    else:
        reconnect = False
    
    main_hwnd = win32console.GetConsoleWindow()
    if main_hwnd and not keep_output:
        win32gui.ShowWindow(main_hwnd, win32con.SW_HIDE)
    
    print_lock = threading.Lock()
    reconnect_lock = threading.Lock()
    
    sys.stdout = Logger(sys.stdout)
    sys.stderr = Logger(sys.stderr)
    sys.stderr.daemon = True
    sys.stderr.start()
    
    if not reconnect:
        with print_lock:
            print(FIRST_LOG_LINE)
            print(str(start_time) + ": Начало работы скрипта...")
    
    internet_connected = shutdown_started = ups_signal_lost = start_agent = dyndns_error = shutdown_vm_flag = False
    reboot_start_time = next_voltage_measure_time = prev_ip_address = speak_russian = last_internet_connect = reconnect_internet_thread = None

    winhide_count = -1 if keep_output else 5
    status = "+"

    with print_lock, get_reg_key() as reg_key:
        try:
            dyndns_data = winreg.QueryValueEx(reg_key, DYNDNS_DATA)[0]
        except WindowsError as error:
            if error.args[0] != 2:
                print(DYNDNS_DATA + ":", error, "!!!")
            status = None
        if status is not None:
            try:
                DYNDNS_HOST_NAMES = idna(winreg.QueryValueEx(reg_key, DYNDNS_HOST_NAMES)[0])
                if not isinstance(DYNDNS_HOST_NAMES, str):
                    status = None
            except WindowsError as error:
                if error.args[0] != 2:
                    print(DYNDNS_HOST_NAMES + ":", error, "!!!")
                status = None
        if status is not None:
            try:
                prev_ip_address = winreg.QueryValueEx(reg_key, DYNDNS_IP_ADDRESS)[0]
            except WindowsError as error:
                if error.args[0] != 2:
                    print(DYNDNS_IP_ADDRESS + ":", error, "!!!")

    speaker_queue = queue.Queue()
    
    sound = Sound()
    sound.daemon = True
    sound.start()
    
    warning_thread = threading.Thread(target=speak_warning)
    warning_thread.daemon = True
    warning_thread.start()

    while True:
        if speak_russian is not None:
            if speak_russian:
                MSG_HEAD = ": Не удалось включить трансляцию сообщений на русском языке"
                for i in range(12):
                    try:
                        gettext.translation(gettext.textdomain(), localedir=os.path.dirname(__file__), languages=["ru"]).install()
                        with print_lock:
                            print(str(datetime.datetime.now()) + ": Трансляция сообщений на русском языке успешно включена...")
                        break
                    except Exception as error:
                        if error.args[0] == 2:
                            time.sleep(15)
                            continue
                        with print_lock:
                            print(str(datetime.datetime.now()) + MSG_HEAD + ", ошибка:\n    " + str(error))
                        speak_russian = False
                        break
                else:
                    with print_lock:
                        print(str(datetime.datetime.now()) + MSG_HEAD + "...")
                    speak_russian = False

            break
        time.sleep(1)
    if not speak_russian:
        gettext.install(gettext.textdomain())
    
    if reconnect:
        router_status(reconnect=True)
        time.sleep(10)
        sys.exit()
    
    site_thread = threading.Thread(target=update_site)
    site_thread.daemon = True
    site_thread.start()
    
    ups = TestUPS()
    ups.daemon = True
    ups.start()
    
    reconnect_thread = threading.Timer(WAIT_FOR_RECONNECT, router_status, kwargs={"reconnect": True})
    reconnect_thread.daemon = True
    reconnect_thread.start()

    print_ip_address_thread = threading.Timer(60, print_ip_address, kwargs={"prev_ip_address": prev_ip_address})
    print_ip_address_thread.daemon = True
    print_ip_address_thread.start()

    modem_thread = threading.Timer(60, modem_status)
    modem_thread.daemon = True
    modem_thread.start()

    manage_vm_thread = threading.Thread(target=manage_vm)
    manage_vm_thread.daemon = True
    manage_vm_thread.start()
    
    nas_check_time_thread = threading.Thread(target=nas_check_time_process)
    nas_check_time_thread.daemon = True
    nas_check_time_thread.start()

    process_events_thread = threading.Timer(120, process_events)
    process_events_thread.daemon = True
    process_events_thread.start()

    for file_name in (SHUTDOWN_FLAG, ):
        if os.path.exists(file_name):
            time.sleep(0.5)
            try:
                os.remove(file_name)
            except WindowsError as error:
                if error.args[0] != 2:
                    raise
    
    while True:
        # Скроем окно, если не удалось ранее
        if winhide_count >= 0 and main_hwnd:
            win32gui.ShowWindow(main_hwnd, win32con.SW_HIDE)
            winhide_count -= 1
        
        # Проверка наличия работающих служб ИБП, поступления данных от ИБП
        now = datetime.datetime.now()
        if next_voltage_measure_time is not None and next_voltage_measure_time < now:
            next_voltage_measure_time = None
        
        voltage_measure_time = get_voltage(time_stamp=True)
        
        if start_agent:
            with print_lock:
                print(str(now) + ": Выполняется запуск Winpower agent и перезапуск скрипта...")
            speaker_queue.put(_("Starting Winpower agent"))
            upsms = multiprocessing.Process(target=subprocess.call, args=(upsdata[2], ))
            upsms.daemon = True
            upsms.start()
            time.sleep(15)
            speaker_queue.put(_("Restarting script"))
            time.sleep(5)
            subprocess.Popen(START_SCRIPT)
            break
        
        delta = datetime.timedelta(minutes=2 if next_voltage_measure_time is None else VM_SHUTDOWN_DELAY)
        ups_data_fresh = now - voltage_measure_time <= delta
        if ups.all_right and ups_data_fresh:
            reboot_start_time = None
            if ups_signal_lost:
                ups_signal_lost = sound.alarm = False
                if shutdown_started:
                    shutdown_computer(abort_shutdown=True)
        elif not reboot_start_time:
            reboot_start_time = now + datetime.timedelta(seconds=UPS_TEST_PERIOD*UPS_SIGNAL_LAG+5)
        elif not ups_signal_lost and now >= reboot_start_time:
            if ups.all_right:
                with print_lock:
                    print(str(now) + ": Данные об измерении напряжения устарели: " + str(voltage_measure_time))
            shutdown_computer()
            ups_signal_lost = sound.alarm = True
        
        now_internet_connected = not ctypes.windll.connect.IsInternetConnected()
        if now_internet_connected != internet_connected:
            internet_connected = now_internet_connected
            with print_lock:
                print(str(datetime.datetime.now()) + ": Интернет " +
                    ("" if now_internet_connected else "не ") + "доступен...")
            if now_internet_connected:
                speaker_queue.put(_("internet is connected"))
            else:
                speaker_queue.put(_("internet is not connected!"))
            reconnect_thread.cancel()
            if not internet_connected:
                reconnect_thread = threading.Timer(WAIT_FOR_RECONNECT, router_status, kwargs={"reconnect": True})
                reconnect_thread.daemon = True
                reconnect_thread.start()
        
        if os.path.exists(SHUTDOWN_FLAG) or (shutdown_started and shutdown):
            time.sleep(0.5)
            try:
                os.remove(SHUTDOWN_FLAG)
            except WindowsError as error:
                if error.args[0] != 2:
                    raise
            if not os.path.exists(SHUTDOWN_FLAG):
                if os.path.exists(NAS_CHECK_TIME_FILE):
                    try:
                        os.remove(NAS_CHECK_TIME_FILE)
                    except WindowsError:
                        pass
                shutdown_nas_thread = threading.Thread(target=shutdown_nas)
                shutdown_nas_thread.daemon = True
                shutdown_nas_thread.start()
                # Обработаем перевод хоста DynDNS в оффлайн
                if not STATIC_ADDRESS and status == "+":
                    status = "-"
                shutdown_vm_flag = True
                next_voltage_measure_time = datetime.datetime.now() + datetime.timedelta(minutes=VM_SHUTDOWN_DELAY)
                close_browsers()

        if shutdown_started:
            if not shutdown and not shutdown_vm_flag:
                close_browsers()
            shutdown_vm_flag = True

        if os.path.exists(DYNDNS_UPDATE_ERROR_FILE) and not dyndns_error:
            dyndns_error = True
            speaker_queue.put(_("DynDNS error, more information in error log"))

        time.sleep(5)