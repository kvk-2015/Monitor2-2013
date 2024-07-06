@echo off
setlocal
set mask=db2diag.log_????-??-??-??.??.??
set _7z=%ProgramFiles%\7-Zip\7z.exe
set arc_name=db2diag.7z
c:
cd "%ProgramData%\IBM\DB2\DB2COPY1\DB2"
db2diag -A
"%_7z%" a -mx9 %arc_name% %mask% && "%_7z%" t %arc_name% && del /q %mask%"
d:
exit /b
forfiles /m %mask% /c "cmd /c ^0x22%_7z: =^ %^0x22 a -mx9 %arc_name% @file && ^0x22%_7z: =^ %^0x22 t %arc_name%" && del /q %mask%"