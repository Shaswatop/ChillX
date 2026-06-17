@echo off
cd /d "C:\Users\Dell\Desktop\OJT PROJECT"
python -m runserver 0.0.0.0:8000 2>server_err.log 1>server_out.log
