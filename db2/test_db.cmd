@echo off
setlocal
db2 list applications for db %1 && exit /b
set active=no
db2 list active databases | findstr /i /r "=\ %1$" >nul && set active=yes
if %active%==yes db2 deactivate db %1 || (db2 activate db %1 & exit /b)
db2 CONNECT TO %1
db2 QUIESCE DATABASE IMMEDIATE FORCE CONNECTIONS
db2 CONNECT RESET
::db2set DB2_DIRECT_IO=OFF
db2dart %1 /RPT . /ERR E
::db2set DB2_DIRECT_IO=
db2 CONNECT TO %1
db2 UNQUIESCE DATABASE
db2 CONNECT RESET
if %active%==yes db2 activate db %1