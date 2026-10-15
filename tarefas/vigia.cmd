@echo off
cd /d "C:\Users\vinic\Projects\YouTube_Agentes"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
"C:\Users\vinic\AppData\Local\Programs\Python\Python312\python.exe" vigia.py >> dados\tarefas.log 2>&1
