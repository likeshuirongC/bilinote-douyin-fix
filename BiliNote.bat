@echo off
rem BiliNote 启动入口
rem  1) 启动器负责把 Docker / 服务 / 抓取浏览器拉起来
rem  2) 再由 bat 自己打开界面 —— 打包 exe 内启动 GUI 不可靠，cmd 的 start 可以
rem 注意：不要用 timeout 做延时（非交互环境下会报 Input redirection 直接退出），用 ping 代替
cd /d "%~dp0"

if not exist "BiliNoteApp\BiliNoteApp.exe" (
  echo [错误] 找不到 BiliNoteApp\BiliNoteApp.exe
  pause
  exit /b 1
)

start "" "BiliNoteApp\BiliNoteApp.exe"

rem 约 8 秒，等服务就绪
ping 127.0.0.1 -n 9 >nul

start "" "http://localhost:3015"
exit /b 0
