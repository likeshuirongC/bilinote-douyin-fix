@echo off
title BiliNote - 抖音抓取专用 Chrome

curl -s --max-time 2 http://127.0.0.1:9222/json/version >nul 2>&1
if not errorlevel 1 (
  echo [跳过] 抖音抓取专用浏览器已在运行。
  exit /b 0
)

set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not exist "%CHROME%" (
  echo [错误] 没找到 Chrome/Edge，请用记事本打开本文件，把 CHROME 改成你的浏览器路径。
  exit /b 1
)

echo 正在启动抖音抓取专用浏览器（后台无窗口，调试端口 9222）...
start "" /b "%CHROME%" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="%LOCALAPPDATA%\BiliNoteDouyinChrome" --headless=new --no-first-run --no-default-browser-check --disable-gpu --mute-audio --lang=zh-CN about:blank >nul 2>&1
echo 已启动。
exit /b 0
