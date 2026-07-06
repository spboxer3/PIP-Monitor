@echo off
setlocal
set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python310\python.exe"
if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" "%~dp0pip_monitor.py"
) else (
    python "%~dp0pip_monitor.py"
)
