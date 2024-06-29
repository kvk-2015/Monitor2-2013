#! python3.5

import datetime
import os
import os.path
import re


if __name__ == "__main__":
    LOG_DIR = "1"
    RE_DATE = re.compile(rb"(\d{4}(?:-\d{2}){2}) (?:\d{2}:){2}\d{2}\.\d{6}:")
    MIN_INTERVAL = 1
    prev_date = None
    for log_name in os.listdir(LOG_DIR):
        if not log_name.endswith(".log"):
            continue
        with open(os.path.join(LOG_DIR, log_name), "rb") as log:
            for date in RE_DATE.findall(log.read()):
                try:
                    cur_date = datetime.datetime.strptime(str(date, encoding="utf_8"), "%Y-%m-%d").date()
                except ValueError:
                    continue
                try:
                    if (cur_date-prev_date)/datetime.timedelta(days=1) > MIN_INTERVAL:
                        print(prev_date, cur_date, (cur_date-prev_date).days)
                except TypeError:
                    pass
                prev_date = cur_date
