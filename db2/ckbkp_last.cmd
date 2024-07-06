@echo off
setlocal
for %%i in (*.001) do set last_backup=%%i
echo --------------- %last_backup% --------------- >> ckbkp_last.log
db2ckbkp %last_backup% >> ckbkp_last.log