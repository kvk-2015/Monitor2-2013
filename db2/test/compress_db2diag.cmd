@echo off
setlocal
set mask=db2diag.log_????-??-??-??.??.??
set Rar=%ProgramFiles%\WinRAR\RAR.exe
set arc_name=db2diag.rar
c:
cd "\Documents and Settings\All Users\Application Data\IBM\DB2\DB2COPY1\DB2"
db2diag -A
"%Rar%" a -m5 %arc_name% %mask% && "%Rar%" t %arc_name% && del /q %mask%"
e:
exit /b
::forfiles /m %mask% /c "cmd /c ^0x22%_7z: =^ %^0x22 a -mx9 %arc_name% @file && ^0x22%_7z: =^ %^0x22 t %arc_name%" && del /q %mask%"