import datetime
import ibm_db
import ibm_db_dbi
import itertools
import re
import time
import home_site.views
from django.contrib import messages
from django.core.cache import cache
from django.http import Http404
from django.utils import six
from django.views.generic.base import TemplateView


class UPSStatisticsPageView(TemplateView):
    template_name='ups_statistics.html'
    MAX_COL_COUNT = 8
    
    def get_context_data(self, **kwargs):
        context = super(UPSStatisticsPageView, self).get_context_data(**kwargs)
        try:
            page_date = datetime.date(int(context['year']), int(context['month']), int(context['day']))
        except (KeyError, TypeError):
            page_date = None
        except ValueError:
            raise Http404
        page_hour = None
        if page_date is not None:
            try:
                page_hour = int(context['hour'])
                page_hour = page_hour - page_hour % 3 + 2
            except (KeyError, TypeError):
                page_hour = None
        try:
            hour_group = context['hour_group']
        except (KeyError, TypeError):
            hour_group = None
        try:
            self.conn = ibm_db.connect('DATABASE=site;HOSTNAME=192.168.0.***;PORT=50000;PROTOCOL=TCPIP;UID=db2user;PWD=***;', '', '')
        except Exception:
            messages.add_message(self.request, messages.ERROR, 'База данных не доступна, ошибка: ' + str(ibm_db.conn_error()))
        else:
            if hour_group is None:
                context['title'] = 'Статистика напряжения сети'
                if page_date is None:
                    context['period'] = 'за последние сутки'
                    now = datetime.datetime.now()
                    remainder = now.hour % 3
                    hour_shift = 3 if remainder == 0 and now.minute < 3 else 0
                    last_update = now.replace(hour=now.hour - remainder, minute=3, second=0, microsecond = 0)
                    next_update = last_update + datetime.timedelta(hours=3 - hour_shift)
                    next_update, wait_for_cache = self.next_update_time(self.request.META['REMOTE_ADDR'],
                                                                        self.request.COOKIES['sessionid'], next_update)
                    str_seconds_to_update = str(max(0, int(round((next_update - datetime.datetime.now()).total_seconds()))))
                    context['refresh'] = str_seconds_to_update
                    if wait_for_cache:
                        for i in range(10):
                            cached_data = cache.get('ups_statistics')
                            if cached_data is not None:
                                context['groups'] = cached_data[0]
                                context['labels'] = cached_data[1]
                                context['data'] = ",\n                        ".join(cached_data[2])
                                try:
                                    ibm_db.close(self.conn)
                                except Exception:
                                    pass
                                return context
                            time.sleep(1)
                    else:
                        cache.delete('ups_statistics')
                elif page_hour is None:
                    context['period'] = 'за ' + page_date.isoformat()
                else:
                    context['period'] = 'на ' + page_date.isoformat() + ', ' + str(page_hour) + ':59'
                FMT = '{0:4.1f}'
                DELTA = 1.3
                groups = self.get_data(page_date=page_date, page_hour=page_hour)
                if isinstance(groups, list):
                    labels = []
                    data = []
                    i = 0
                    for group in groups:
                        labels.append(group[1])
                        i_ave = float(group[5])
                        data.append('[' + str(15 * i + 7) + ', [' + group[3] + ', ' + FMT.format(i_ave - DELTA) + ', ' + group[5] + ', ' +
                                    FMT.format(i_ave + DELTA) + ', ' + group[4] + ', r, r], r]')
                        o_ave = float(group[8])
                        data.append('[' + str(15 * i + 8) + ', [' + group[6] + ', ' + FMT.format(o_ave - DELTA) + ', ' + group[8] + ', ' +
                                    FMT.format(o_ave + DELTA) + ', ' + group[7] + ', g, g], g]')
                        i += 1
                    context['groups'] = groups
                    context['labels'] = labels
                    context['data'] = ",\n                        ".join(data)
                    cache.set('ups_statistics', (groups, labels, data), 600)
            else:
                self.template_name = "ups_statistics_detailed.html"
                context['title'] = 'Подробно напряжение сети'
                result = self.get_data(detailed=hour_group)
                if isinstance(result, list):
                    context['date'] = result[0][3]
                    context['start_time'] = result[0][0]
                    context['end_time'] = result[0][1]
                    context['total'] = result[0][2]
                    labels = set()
                    for voltage in result[1] + result[2]:
                        labels.add(int(voltage[0]))
                    if six.PY3:
                        labels = list(map(str, sorted(list(labels))))
                    else:
                        labels = map(str, sorted(list(labels)))
                    if len(labels) % 2:
                        labels.insert(0, str(int(labels[0])-1))
                    groups = []
                    span_key = (x//20 for x in itertools.count())
                    for k, g in itertools.groupby(labels, lambda x: next(span_key)):
                        groups.append(', '.join(list(g)))
                    context['labels'] = ",\n                                    ".join(groups)
                    context['labels_len'] = len(labels)
                    context['labels_len_div_2'] = int(len(labels)/2)
                    canvas_width = 700 + max(0, 12 * (len(labels) - 58) - 4)
                    context['canvas_width'] = canvas_width
                    context['hmargin'] = int(canvas_width/len(labels)/2)
                    data = [[], []]
                    for i in range(2):
                        temp = dict(result[i + 1])
                        for voltage in labels:
                            data[i].append(str(temp.get(voltage, 'null')))
                    for i in range(2):
                        groups = []
                        span_key = (x//20 for x in itertools.count())
                        for k, g in itertools.groupby(data[i], lambda x: next(span_key)):
                            groups.append(', '.join(list(g)))
                        context['output' if i else 'input'] = ",\n                            ".join(groups)
                    for i in range(3):
                        groups = []
                        span_key = (x//(20 if i else 10) for x in itertools.count())
                        for k, g in itertools.groupby(result[3][i], lambda x: next(span_key)):
                            if i:
                                groups.append(', '.join(list(g)))
                            else:
                                groups.append('"' + '", "'.join(list(g)) + '"')
                        if i:
                            context['output1' if i-1 else 'input1'] = ",\n                            ".join(groups)
                        else:
                            context['labels1'] = ",\n                            ".join(groups)
                    labels2 = []
                    LABELS_NO = 21
                    for i in range(LABELS_NO):
                        labels2.append('"' + result[3][0][int(round(i * (len(result[3][0]) - 1) / (LABELS_NO - 1)))] + '"')
                    groups = []
                    span_key = (x//8 for x in itertools.count())
                    for k, g in itertools.groupby(labels2, lambda x: next(span_key)):
                        groups.append(', '.join(list(g)))
                    context['labels2'] = ",\n                                        ".join(groups)
                    missing = []
                    for gap in result[4][0]:
                        missing.append(str(gap[0]) + " (" + gap[1] + ")")
                    context['missing'] = missing
                    context['every_second'] = result[4][1]
        try:
            ibm_db.close(self.conn)
        except Exception:
            pass
        return context
    get_context_data.alters_data = True

    def next_update_time(self, remote_addr, id, update_time):
        LAST_UPDATES_DEPTH = 25  # Период храниения информиции о последних подключениях, секунды
        AVERAGE_SCRIPT_RUN_TIME = 1.0  # Среднее время выполнения скрипта, секунды
        FIRST_SCRIPT_RUN_TIME = 8.0  # Время выполнения скрипта для первого запроса из группы, секунды
        CACHE_TIMEOUT = datetime.timedelta(seconds=600)
    
        conn_dbi = ibm_db_dbi.Connection(self.conn)
        # CREATE TABLE IPPON.SITE_DATA (ADDR_TYPE CHAR(1), ADDR VARCHAR(15), ID CHAR(32), RECORD_TYPE CHAR(1), NEXT_UPDATE TIMESTAMP(0))
        # все NOT NULL
        # RECORD_TYPE:
        # 0 - текущий трехчасовой отрезок
        # 1 - следующий
        # CREATE TABLE IPPON.LAST_UPDATES (ID CHAR(32), LAST_UPDATE TIMESTAMP(0)) # все NOT NULL
    
        cur = conn_dbi.cursor()
        cur.execute('SELECT ID FROM IPPON.LAST_UPDATES FETCH FIRST 1 ROW ONLY FOR UPDATE WITH RR USE AND KEEP EXCLUSIVE LOCKS')
        select_current_start = '''
            SELECT NEXT_UPDATE FROM IPPON.SITE_DATA WHERE RECORD_TYPE = 1 ORDER BY NEXT_UPDATE
                FETCH FIRST 1 ROW ONLY '''
        cur.execute(select_current_start)
        row = cur.fetchone()
        if row and row[0] < update_time:
            cur.execute(select_current_start + 'FOR UPDATE WITH RR USE AND KEEP EXCLUSIVE LOCKS')
            row = cur.fetchone()
            if row and row[0] < update_time:
                cur.execute('DELETE FROM IPPON.SITE_DATA WHERE RECORD_TYPE = 0')
                cur.execute('UPDATE IPPON.SITE_DATA SET RECORD_TYPE = 0 WHERE RECORD_TYPE = 1 AND NEXT_UPDATE < ?', (update_time, ))
                cur.execute('DELETE FROM IPPON.LAST_UPDATES')
    
        now = datetime.datetime.now()
        cur.execute('DELETE FROM IPPON.LAST_UPDATES WHERE LAST_UPDATE < ?', (now - CACHE_TIMEOUT, ))
        cur.execute('INSERT INTO IPPON.LAST_UPDATES (ID, LAST_UPDATE) VALUES (?, ?)', (id, now))
        cur.execute('SELECT COUNT(*) FROM IPPON.LAST_UPDATES')
        conn_dbi.commit()
        wait_for_cache = cur.fetchone()[0] > 1
    
        cur.execute('SELECT NEXT_UPDATE FROM IPPON.SITE_DATA WHERE ADDR = ? AND ID = ? AND RECORD_TYPE = 1', (remote_addr, id))
        row = cur.fetchone()
        if row:
            update_time = row[0]
        else:
            # Выстроим приоритеты
            if remote_addr == '127.0.0.1':
                addr_type = 0
                cur.execute('SELECT COUNT(*) FROM IPPON.SITE_DATA WHERE ADDR_TYPE = 0 AND RECORD_TYPE = 1')
            elif re.match(r"10\.|169\.254\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.", remote_addr):
                addr_type = 1
                cur.execute('''
                SELECT SUM(CLIENTS) FROM (
                    SELECT MAX(LOCALS) AS CLIENTS FROM (
                        SELECT COUNT(*) AS LOCALS FROM IPPON.SITE_DATA WHERE ADDR_TYPE = 0 AND RECORD_TYPE = 0
                        UNION
                        SELECT COUNT(*) FROM IPPON.SITE_DATA WHERE ADDR_TYPE = 0 AND RECORD_TYPE = 1
                    )
                    UNION ALL
                    SELECT COUNT(*) FROM IPPON.SITE_DATA WHERE ADDR_TYPE = 1 AND RECORD_TYPE = 1
                )
                ''')
            else:
                addr_type = 2
                cur.execute('''
                SELECT SUM(CLIENTS) FROM (
                    SELECT MAX(LOCAL_NETS) AS CLIENTS FROM (
                        SELECT COUNT(*) AS LOCAL_NETS FROM IPPON.SITE_DATA WHERE ADDR_TYPE IN (0, 1) AND RECORD_TYPE = 0
                        UNION
                        SELECT COUNT(*) FROM IPPON.SITE_DATA WHERE ADDR_TYPE IN (0, 1) AND RECORD_TYPE = 1
                    )
                    UNION ALL
                    SELECT COUNT(*) FROM IPPON.SITE_DATA WHERE ADDR_TYPE = 2 AND RECORD_TYPE = 1
                )
                ''')
            update_number = cur.fetchone()[0]
            if update_number:
                update_time += datetime.timedelta(seconds=AVERAGE_SCRIPT_RUN_TIME * (update_number - 1) + FIRST_SCRIPT_RUN_TIME)
            cur.execute('INSERT INTO IPPON.SITE_DATA (ADDR, ID, NEXT_UPDATE, ADDR_TYPE, RECORD_TYPE) VALUES (?, ?, ?, ?, 1)',
                        (remote_addr, id, update_time, addr_type))
            conn_dbi.commit()
        return (update_time, wait_for_cache)
    next_update_time.alters_data = True

    def time_string(self, time_stamp):
        return time_stamp.strftime("%H:%M:%S")

    def get_data(self, detailed=None, page_date=None, page_hour=None):
        EVERY_SECOND_START_HOUR = 117827
    
        select = "SELECT MIN(HOUR_GROUP) FROM IPPON.VOLTAGE"
        stmt = ibm_db.exec_immediate(self.conn, select)
        first_hour_group = ibm_db.fetch_tuple(stmt)
        if isinstance(first_hour_group, tuple):
            first_hour_group = first_hour_group[0]
        else:
            messages.add_message(self.request, messages.INFO, 'Данные отсутствуют')
            return
        if page_date is None:
            end_time = datetime.datetime.now()
        elif page_hour is None:
            end_time = datetime.datetime(page_date.year, page_date.month, page_date.day, 23, 59) + datetime.timedelta(minutes=2)
        else:
            end_time = datetime.datetime(page_date.year, page_date.month, page_date.day, page_hour, 59) + datetime.timedelta(minutes=2)
        if six.PY3:
            last_hour_group = int((end_time - datetime.datetime(2000, 1, 1)) / datetime.timedelta(hours=1)) - end_time.hour % 3 - 1
        else:
            time_span = end_time - datetime.datetime(2000, 1, 1)
            last_hour_group = time_span.days * 24 + int(time_span.seconds/3600) - end_time.hour % 3 - 1
        if detailed is not None:
            index = int(detailed)
            if index > last_hour_group:
                messages.add_message(self.request, messages.WARNING, 'Ошибочный индекс=' + detailed)
                return
            remainder = index % 3
            if remainder != 2:
                index += 2 - remainder
            last_hour_group = index
        if last_hour_group < first_hour_group:
            messages.add_message(self.request, messages.INFO, 'Нет данных за требуемый период')
            return
        select = """
        WITH T(START_GROUP, END_GROUP) AS (SELECT END_GROUP-2, END_GROUP FROM (VALUES(?)) AS T(END_GROUP))
        SELECT COUNT(*) TOTAL, SUM(AVR) AVR, MIN(LOCAL_TIME) START_TIME, MAX(LOCAL_TIME) END_TIME,
            CAST(ROUND(AVG(NULLIF(DECIMAL(INPUT_VOLTAGE), 0)), 1) AS DECIMAL(4,1)) INPUT_AVG,
                MAX(NULLIF(INPUT_VOLTAGE, 0)) INPUT_MAX, MIN(NULLIF(INPUT_VOLTAGE, 0)) INPUT_MIN,
            CAST(ROUND(AVG(NVL2(NULLIF(INPUT_VOLTAGE, 0), DECIMAL(OUTPUT_VOLTAGE), NULL)), 1) AS DECIMAL(4,1)) OUTPUT_AVG,
                MAX(NVL2(NULLIF(INPUT_VOLTAGE, 0), OUTPUT_VOLTAGE, NULL)) OUTPUT_MAX,
                MIN(NVL2(NULLIF(INPUT_VOLTAGE, 0), OUTPUT_VOLTAGE, NULL)) OUTPUT_MIN,
            SUM(SIGN(INPUT_VOLTAGE)) ONLINE
            FROM IPPON.VOLTAGE, T WHERE HOUR_GROUP BETWEEN START_GROUP AND END_GROUP"""
        all_stat = ibm_db.prepare(self.conn, select)
        col_count = 0
        lines = []
        range_or_index = [last_hour_group] if detailed is not None else range(last_hour_group, last_hour_group-169 , -3)
        for i in range_or_index:
            if col_count >= self.MAX_COL_COUNT:
                break
            ibm_db.execute(all_stat, (i,))
            row = ibm_db.fetch_assoc(all_stat)
            if not row or row["TOTAL"] < (900 if i >= EVERY_SECOND_START_HOUR else 90):
                continue
            portion_timestamp = row["END_TIME"]
            portion = [self.time_string(row["START_TIME"]), self.time_string(portion_timestamp),
                str(row["TOTAL"]), str(row["INPUT_MIN"]), str(row["INPUT_MAX"]), row["INPUT_AVG"].replace(",", "."),
                str(row["OUTPUT_MIN"]), str(row["OUTPUT_MAX"]), row["OUTPUT_AVG"].replace(",", "."),
                "{0:.1f}".format(100*row["AVR"]/row["ONLINE"] if row["ONLINE"] else 0), str(i)]
            if detailed is None:
                lines.insert(0, portion)
            else:
                select = """
                WITH T(START_GROUP, END_GROUP) AS (SELECT END_GROUP-2, END_GROUP FROM (VALUES(?)) AS T(END_GROUP))
                SELECT COALESCE(I, O) VOLTAGE_TYPE, COALESCE(INPUT_VOLTAGE, OUTPUT_VOLTAGE) VOLTAGE, COUNT(*) VOLTAGE_COUNT
                    FROM IPPON.VOLTAGE, T, (VALUES(0, 1)) AS VOLTAGE_TYPES(I, O)
                    WHERE INPUT_VOLTAGE > 0 AND HOUR_GROUP BETWEEN START_GROUP AND END_GROUP
                    GROUP BY GROUPING SETS ((I, INPUT_VOLTAGE), (O, OUTPUT_VOLTAGE))
                    ORDER BY VOLTAGE_TYPE, VOLTAGE"""
                detailed_data = ibm_db.prepare(self.conn, select)
                ibm_db.execute(detailed_data, (i,))
                data = [[], []]
                row = ibm_db.fetch_tuple(detailed_data)
                while row:
                    data[row[0]].append([str(row[1]), str(row[2])])
                    row = ibm_db.fetch_tuple(detailed_data)
                select = """
                WITH T(START_GROUP, END_GROUP) AS (SELECT END_GROUP-2, END_GROUP FROM (VALUES(?)) AS T(END_GROUP))
                SELECT CAST(LOCAL_TIME AS TIME), INPUT_VOLTAGE, OUTPUT_VOLTAGE
                    FROM IPPON.VOLTAGE, T
                    WHERE HOUR_GROUP BETWEEN START_GROUP AND END_GROUP
                    ORDER BY LOCAL_TIME"""
                detailed_data = ibm_db.prepare(self.conn, select)
                ibm_db.execute(detailed_data, (i,))
                line_data = [[], [], []]
                row = ibm_db.fetch_tuple(detailed_data)
                while row:
                    for j in range(3):
                        line_data[j].append(str(row[j]))
                    row = ibm_db.fetch_tuple(detailed_data)
                every_second = i >= EVERY_SECOND_START_HOUR
                if every_second:
                    times = "CAST(D.DIFF-1 AS DECIMAL(5))"
                    diff = 5
                else:
                    times = "CAST(ROUND(D.DIFF, -1)/10-1 AS DECIMAL(3))"
                    diff = 18
                select = """
                WITH T(START_GROUP, END_GROUP) AS (SELECT END_GROUP-2, END_GROUP FROM (VALUES(?)) AS T(END_GROUP))
                SELECT CAST(C.LOCAL_TIME AS TIME), {0} TIMES
                    FROM IPPON.VOLTAGE C
                    INNER JOIN
                    (SELECT A.LOCAL_TIME L_TIME,
                        TIMESTAMPDIFF(2, CHAR(A.LOCAL_TIME - LAG(B.LOCAL_TIME) OVER (ORDER BY B.LOCAL_TIME))) DIFF
                        FROM T JOIN IPPON.VOLTAGE A ON 1 = 1 INNER JOIN IPPON.VOLTAGE B
                        ON A.LOCAL_TIME = B.LOCAL_TIME AND A.HOUR_GROUP BETWEEN START_GROUP AND END_GROUP) D
                    ON C.LOCAL_TIME = D.L_TIME AND D.DIFF > {1}""".format(times, diff)
                detailed_data = ibm_db.prepare(self.conn, select)
                ibm_db.execute(detailed_data, (i,))
                missing_measures = [], every_second
                row = ibm_db.fetch_tuple(detailed_data)
                while row:
                    missing_measures[0].append(row)
                    row = ibm_db.fetch_tuple(detailed_data)
                return [portion[:3] + [portion_timestamp.strftime("%d.%m.%Y")], data[0], data[1], line_data, missing_measures]
            col_count += 1
        return lines