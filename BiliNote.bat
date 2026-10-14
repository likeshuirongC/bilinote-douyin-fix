@echo off
rem BiliNote 启动入口
rem   1) 拉起抖音抓取专用 Chrome（必须在 cmd 里做：从打包 exe 里启动 GUI 程序不可靠，
rem      实测 Chrome 起不来，只会在日志里留一句"已执行"）
rem   2) 启动器负责 Docker / 后端服务 / 健康检查
rem   3) 等服务就绪后用浏览器打开界面
rem 注意：不要用 timeout 做延时（非交互环境会报 Input redirection 直接退出），用 ping
cd /d "%~dp0"

if not exist "BiliNoteApp\BiliNoteApp.exe" (
  echo [错误] 找不到 BiliNoteApp\BiliNoteApp.exe
  pause
  exit /b 1
)

if exist "start-douyin-chrome.bat" (
  call "start-douyin-chrome.bat"
)

start "" "BiliNoteApp\BiliNoteApp.exe"

rem 约 8 秒，等服务就绪
ping 127.0.0.1 -n 9 >nul

start "" "http://localhost:3015"
exit /b 0
