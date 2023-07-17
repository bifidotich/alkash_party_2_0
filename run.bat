cd /d %~dp0
call venv\Scripts\activate.bat
cd aikash
call python main.py
cmd.exe