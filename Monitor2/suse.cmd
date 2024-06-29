@echo off
setlocal
set flag_file="D:\kvk\Utilities\Monitor2\Monitor2.stop_vm"
if "%1" == "off" (echo. > %flag_file%) else (del /q %flag_file% 2>nul)