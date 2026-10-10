@echo off
rem 从命令行方式拉起 BiliNote 启动器，绕过 SmartScreen 对未签名 exe 的拦截
cd /d "%~dp0"
if exist "BiliNoteApp\BiliNoteApp.exe" (
  start "" "BiliNoteApp\BiliNoteApp.exe"
) else (
  echo [错误] 找不到 BiliNoteApp\BiliNoteApp.exe
  pause
)
exit /b 0
