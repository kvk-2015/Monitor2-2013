@echo off
setlocal
set DB2INSTANCE=DB2
set db=testnext
set backup_path=E:\backup.db2\
db2 list applications for db %db% && exit /b
set active=no
db2 list active databases | findstr /i /r "=\ %db%$" >nul && set active=yes
if %active%==yes db2 deactivate db %db% || (db2 activate db %db% & exit /b)
db2 CONNECT TO %db%
db2 QUIESCE DATABASE IMMEDIATE FORCE CONNECTIONS
db2 CONNECT RESET
db2 BACKUP DATABASE %db% TO "%backup_path%%db%\offline" COMPRESS >> "%backup_path%%db%\offline\backup.log"
db2 CONNECT TO %db%
db2 UNQUIESCE DATABASE
db2 CONNECT RESET
if %active%==yes db2 activate db %db%