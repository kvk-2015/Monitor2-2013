@echo off
setlocal&&set DB2INSTANCE=DB2INST2&&db2 BACKUP DATABASE test106 ONLINE TO "E:\backup.db2\test106" COMPRESS >> "E:\backup.db2\test106\backup.log"