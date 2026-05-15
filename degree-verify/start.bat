@echo off
title DegreeChain Launcher

echo.
echo  Starting Ganache blockchain...
start "Ganache" cmd /k "ganache --port 7545"

echo  Waiting for Ganache to boot...
timeout /t 3 /nobreak > nul

echo  Starting Flask server...
start "DegreeChain" cmd /k "cd /d D:\CT\Porjectt1\degree-verify && D:\CT\Porjectt1\.venv\Scripts\python.exe app1.py"

echo  Opening browser...
timeout /t 5 /nobreak > nul
start http://127.0.0.1:5000

echo.
echo  Both terminals are running. Close them to stop the project.
