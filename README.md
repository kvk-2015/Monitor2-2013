# Monitor2-2013
2013-12-07 partial "snapshot" of my pet project

Script Monitor2.py collected voltage info from UPS Ippon Smart Winner 750, managed ADSL modem,
updated DynDNS status, started and stopped VMware Player (where Apache http server with my Django home_site runed that time)
when BeholdTV tuner made recordings, and more...

home_site/ups_statistics showes the results of voltage monitoring

As a result settings of Volt control equipment were tuned: https://dzen.ru/a/YxoadV2THUlQT6EC

Since 2014 home_site migrated to Raspberry Pi (Arch Linux ARM). Some scripts form 2016 are in Monitor_linux and
Video processing (Windows WSH scripts) folders now...

Some scripts used with IBM DB2 Express-C 10.5fp4 as Dgango supported database that time are stored in db2 folder now
(as for perfomance tuning, all scripts except performance.cmd and db2CollectPerfomanceData.js are from the book
DB2BP_System_Performance_0813.pdf, which is included too)...

Included threaded Logger class, that allows to find out the time of the last activity of the script (it writes to the end of log file every minute).

JScript (WSH) toc generator for video files (lengths through GetDetailsOf or ffprobe.exe summed up) with very compact RegExp word wrap functon.