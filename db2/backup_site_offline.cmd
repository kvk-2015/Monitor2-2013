@echo off
setlocal
set db=site
set backup_path=K:\backup.db2\
db2 list applications for db %db% && exit /b
set active=no
db2 list active databases | findstr /i /r "=\ %db%$" >nul && set active=yes
if %active%==yes db2 deactivate db %db% || (db2 activate db %db% & exit /b)
db2 BACKUP DATABASE %db% TO "%backup_path%%db%\offline" COMPRESS >> "%backup_path%%db%\offline\backup.log"
if %active%==yes db2 activate db %db%