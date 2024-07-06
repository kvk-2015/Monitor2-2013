@echo off
setlocal
set DB2INSTANCE=DB2
db2 BACKUP DATABASE testnext ONLINE TO "E:\backup.db2\testnext" COMPRESS >> "E:\backup.db2\testnext\backup.log"