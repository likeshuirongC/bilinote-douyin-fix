@echo off
title BiliNote
cd /d "%~dp0"

echo ============================================
echo    BiliNote  -  AI 视频笔记
echo ============================================
echo.

echo [1/5] 检查 Docker Desktop...
tasklist /FI "IMAGENAME eq Docker Desktop.exe" 2>nul | find /I "Docker Desktop.exe" >nul
if errorlevel 1 (
  echo   未运行，正在启动 Docker Desktop...
  if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  ) else (
    echo   [警告] 找不到 Docker Desktop，请手动启动。
  )
) else (
  echo   Docker Desktop 已在运行
)

set /a w=0
:waitdocker
docker info >nul 2>&1
if not errorlevel 1 goto dockerok
set /a w+=1
if %w% gtr 45 (
  echo   [警告] Docker 引擎等待超时，请手动打开 Docker Desktop 后重试。
  goto dockerok
)
timeout /t 2 >nul
goto waitdocker
:dockerok

echo [2/5] 启动后端服务...
docker compose up -d >nul 2>&1

echo [3/5] 启动抖音抓取专用浏览器...
call "%~dp0start-douyin-chrome.bat" >nul 2>&1

echo [4/5] 等待服务就绪...
set /a n=0
:wait
timeout /t 2 >nul
set /a n+=1
curl -s --max-time 3 http://127.0.0.1:3015/api/sys_health >nul 2>&1
if not errorlevel 1 goto ready
if %n% lss 30 goto wait
echo   [警告] 等待超时，仍然尝试打开界面。

:ready
echo [5/5] 打开 BiliNote 界面...
start "" http://localhost:3015
exit /b 0
