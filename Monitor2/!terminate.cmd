@echo off
setlocal
for /f "skip=1 usebackq" %%i in (`wmic process where "name='python.exe' and commandline like '%%Monitor2.py%%'" get processid`) do (taskkill /pid %%i /t /f && exit /b)
