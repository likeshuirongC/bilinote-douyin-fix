@echo off
chcp 65001 >nul
title BiliNote - 抖音抓取专用 Chrome

set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not exist "%CHROME%" (
  echo [错误] 没找到 Chrome/Edge，请用记事本打开本脚本，把 CHROME 改成你的浏览器路径。
  pause
  exit /b 1
)

echo 正在启动抖音抓取专用浏览器（无窗口，调试端口 9222）...
echo 浏览器路径: %CHROME%
echo.
echo 说明：
echo   - 这个窗口可以最小化，关掉它不影响已启动的浏览器。
echo   - 浏览器会常驻后台，BiliNote 抓抖音时自动连它。
echo   - 想彻底停止：任务管理器里结束带 remote-debugging-port=9222 的 chrome 进程。

start "" "%CHROME%" ^
  --remote-debugging-port=9222 ^
  --remote-debugging-address=0.0.0.0 ^
  --user-data-dir="%LOCALAPPDATA%\BiliNoteDouyinChrome" ^
  --headless=new ^
  --no-first-run ^
  --no-default-browser-check ^
  --disable-gpu ^
  --mute-audio ^
  --lang=zh-CN ^
  about:blank

echo 已启动。
timeout /t 3 >nul
