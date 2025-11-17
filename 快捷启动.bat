@echo off
cd /d %~dp0

:: 进入 backend 文件夹并运行 python app.py
cd backend
start cmd /K "python app.py"
cd ..

:: 进入 frontend 文件夹并运行 npm run dev
cd frontend
start cmd /K "npm run dev"
cd ..
