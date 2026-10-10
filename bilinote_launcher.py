# -*- coding: utf-8 -*-
"""BiliNote 桌面启动器。

双击后自动完成：
  1) 确保 Docker Desktop 在运行（没开就拉起来并等待引擎就绪）
  2) 启动 BiliNote 服务（docker compose up -d）
  3) 启动抖音抓取专用 Chrome（调试端口 9222）
  4) 等待后端健康检查通过
  5) 以独立窗口打开 BiliNote 界面（无地址栏，接近桌面应用体验）

排查用日志：%TEMP%\bilinote_launcher.log
"""
import os
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import traceback
import urllib.request

APP_URL = "http://localhost:3015"
HEALTH_URL = "http://127.0.0.1:3015/api/sys_health"
DOCKER_DESKTOP = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
CREATE_NO_WINDOW = 0x08000000
def _log_path():
    """日志固定写到用户主目录。

    PyInstaller 冻结后 TEMP 可能被指向内部解压目录（进程退出即清空），
    项目目录也可能因权限/占用写不进去，主目录最稳。
    """
    try:
        if getattr(sys, "frozen", False):
            base = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "bilinote_launcher.log")
    except Exception:
        return os.path.join(tempfile.gettempdir(), "bilinote_launcher.log")

BROWSER_CANDIDATES = [
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass


def find_project_dir():
    """定位 BiliNote 项目根目录（含 docker-compose.yml 的那层）。

    onedir 打包时 exe 位于 BiliNoteApp\\ 子目录，所以要在自身和上一级里找。
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    for cand in (base, os.path.dirname(base)):
        if cand and os.path.exists(os.path.join(cand, "docker-compose.yml")):
            return cand
    return base


PROJECT_DIR = find_project_dir()
LOG_PATH = _log_path()
# 模块级就落一条日志：万一进程在入口前就挂掉，也能看出到底走到哪
try:
    with open(LOG_PATH, "a", encoding="utf-8") as _f:
        _f.write("%s  === 模块加载 frozen=%s PROJECT_DIR=%s\n"
                 % (time.strftime("%H:%M:%S"), getattr(sys, "frozen", False), PROJECT_DIR))
except Exception:
    pass


def find_browser():
    for path in BROWSER_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def run(cmd, timeout=None, cwd=None):
    try:
        # 必须显式 DEVNULL：--noconsole 打包后本进程没有有效 stdin/stderr，
        # 子进程继承过去会让 docker 之类的命令直接卡死（表现为启动器一直停在"检查 Docker"）。
        p = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL,
                           text=True, errors="replace", timeout=timeout, cwd=cwd,
                           creationflags=CREATE_NO_WINDOW)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "timeout"
    except Exception as exc:  # noqa: BLE001
        return -1, str(exc)


def docker_ready():
    code, _ = run(["docker", "info"], timeout=15)
    return code == 0


def process_running(image_name):
    code, out = run(["tasklist", "/FI", "IMAGENAME eq %s" % image_name], timeout=15)
    return code == 0 and image_name.lower() in (out or "").lower()


def health_ok():
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=4) as resp:
            return resp.status == 200
    except Exception:
        return False


def open_app_window():
    browser = find_browser()
    log("open_app_window: browser=%s" % browser)
    if not browser:
        os.startfile(APP_URL)
        log("无浏览器，已用 shell 打开 URL")
        return "browser"
    # 关键：必须用【独立 user-data-dir】启动。
    # Chrome 的单例是按其 profile 判定的：如果复用抓取专用的那个实例
    # （headless、没有可见窗口），--app 请求就被丢进去，窗口根本不出现 ——
    # 而 ShellExecuteW 仍然返回成功，极具迷惑性。
    # DETACHED_PROCESS 让浏览器彻底脱离本进程，避免 --noconsole 冻结环境的句柄问题。
    base_dir = (os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP")
                or tempfile.gettempdir() or os.path.expanduser("~"))
    profile = os.path.join(base_dir, "BiliNoteAppChrome")
    log("profile 路径 = %r (LOCALAPPDATA=%r TEMP=%r)"
        % (profile, os.environ.get("LOCALAPPDATA"), os.environ.get("TEMP")))
    # 把浏览器自身的输出落到文件，启动失败时能直接看到原因
    here = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    try:
        chrome_log = open(os.path.join(here, "chrome_launch.log"), "ab")
    except Exception:
        chrome_log = subprocess.DEVNULL
    # 注：从 --noconsole 的冻结进程里启动 Chrome（无论是 Popen 还是 ShellExecuteW），
    # 实测都会"返回成功但窗口不出现"（Chrome 侧不留进程，也看不到报错）。
    # 与其赌它，不如直接用系统默认浏览器打开 —— 这条路径 100% 可靠。
    # 想用独立窗口的话，手动把 URL 拖进 Chrome 即可。
    try:
        import ctypes
        params = ('--user-data-dir="%s" --no-first-run --no-default-browser-check '
                  '--app=%s --window-size=1280,900' % (profile, APP_URL))
        rc = ctypes.windll.shell32.ShellExecuteW(None, "open", browser, params, None, 1)
        log("先尝试独立窗口 ShellExecuteW -> rc=%s" % rc)
        time.sleep(2)
    except Exception as exc:
        log("独立窗口尝试失败(忽略): %s" % exc)
    try:
        os.startfile(APP_URL)
        log("已用默认浏览器打开 %s" % APP_URL)
        time.sleep(2)
        return "browser"
    except Exception as exc:
        log("默认浏览器打开也失败: %s" % exc)
        return "fail"
    log("改用默认浏览器打开")
    os.startfile(APP_URL)
    return "browser"


class Launcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BiliNote")
        self.root.geometry("380x150")
        self.root.resizable(False, False)
        self.status = tk.StringVar(value="正在准备…")
        tk.Label(self.root, text="BiliNote", font=("Microsoft YaHei UI", 16, "bold")).pack(pady=(18, 4))
        tk.Label(self.root, textvariable=self.status, font=("Microsoft YaHei UI", 9),
                 fg="#555555", wraplength=340, justify="center").pack(padx=16)
        self.bar = tk.Canvas(self.root, width=320, height=6, bg="#e5e7eb", highlightthickness=0)
        self.bar.pack(pady=14)
        self.pill = self.bar.create_rectangle(0, 0, 0, 6, fill="#2563eb", width=0)

    def set_status(self, text, progress=None):
        def apply():
            try:
                self.status.set(text)
                if progress is not None:
                    width = int(320 * max(0.0, min(1.0, progress)))
                    self.bar.coords(self.pill, 0, 0, width, 6)
            except Exception:
                pass
        try:
            self.root.after(0, apply)
        except Exception:
            pass

    def work(self):
        try:
            log("=== 启动流程开始, PROJECT_DIR=%s" % PROJECT_DIR)

            # 服务已经在跑就直接开界面 —— 日常使用走这条路径，秒开
            if health_ok():
                log("服务已就绪，直接打开界面")
                self.set_status("服务已就绪，正在打开界面…", 0.9)
            else:
                self.set_status("检查 Docker Desktop…", 0.05)
                ready, _out = run(["docker", "version", "--format", "{{.Server.Version}}"], timeout=20)
                log("docker version -> code=%s out=%s" % (ready, (_out or "")[:80].replace("\n", " ")))
                if ready != 0:
                    if not process_running("Docker Desktop.exe") and os.path.exists(DOCKER_DESKTOP):
                        self.set_status("正在启动 Docker Desktop（约需 1 分钟）…", 0.1)
                        subprocess.Popen([DOCKER_DESKTOP], creationflags=CREATE_NO_WINDOW,
                                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL)
                        log("已拉起 Docker Desktop")
                    waited = 0
                    while waited < 120 and run(["docker", "version", "--format", "{{.Server.Version}}"],
                                               timeout=20)[0] != 0:
                        time.sleep(4)
                        waited += 4
                        self.set_status("等待 Docker 引擎就绪… %ds" % waited, 0.1 + min(waited / 120, 1) * 0.3)

                self.set_status("启动 BiliNote 服务…", 0.45)
                code, out = run(["docker", "compose", "up", "-d"], timeout=180, cwd=PROJECT_DIR)
                log("docker compose up -d -> %s %s" % (code, (out or "")[-160:].replace("\n", " ")))

            self.set_status("启动抖音抓取浏览器…", 0.6)
            bat = os.path.join(PROJECT_DIR, "start-douyin-chrome.bat")
            if os.path.exists(bat):
                subprocess.run(["cmd", "/c", bat], capture_output=True,
                               stdin=subprocess.DEVNULL, timeout=60,
                               cwd=PROJECT_DIR, creationflags=CREATE_NO_WINDOW)
                log("已执行 start-douyin-chrome.bat")

            self.set_status("等待服务就绪…", 0.7)
            waited = 0
            while not health_ok() and waited < 90:
                time.sleep(2)
                waited += 2
                self.set_status("等待服务就绪… %ds" % waited, 0.7 + min(waited / 90, 1) * 0.28)
            log("health_ok=%s (等了 %ds)" % (health_ok(), waited))

            self.set_status("正在打开 BiliNote 界面…", 1.0)
            mode = open_app_window()
            # 按实际走的分支给提示，别再一律写"用浏览器打开"（误导用户）
            if mode == "app":
                self.set_status("BiliNote 窗口已打开\n任务栏里找不到的话按 Alt+Tab 切一下", 1.0)
            else:
                self.set_status("已在默认浏览器中打开 BiliNote\n请查看浏览器窗口", 1.0)
            time.sleep(4)
            log("=== 启动流程结束")
        except Exception:
            log("work() 异常:\n" + traceback.format_exc())
        finally:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                pass

    def run(self):
        threading.Thread(target=self.work, daemon=True).start()
        self.root.mainloop()


if __name__ == "__main__":
    try:
        Launcher().run()
    except Exception:
        log("FATAL:\n" + traceback.format_exc())
        sys.exit(1)
