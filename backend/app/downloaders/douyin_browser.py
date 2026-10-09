# -*- coding: utf-8 -*-
"""通过真实浏览器 + CDP 抓取抖音视频详情。

背景：抖音网页版接口 aweme/v1/web/aweme/detail/ 现在要求 secsdk 的
x-secsdk-web-signature 三件套签名（a_bogus 已不够），纯 HTTP 复刻成本极高，
表现为 403 Blocked by ArgusSecurityPlugin。

做法：让真实浏览器访问视频页，页面自身 JS 会带着合法签名请求该接口，
我们通过 Chrome DevTools Protocol 监听网络响应并取回 JSON，
结构与原接口一致，可直接替换 fetch_video_info 的返回值。

两种运行模式：
1) DOUYIN_CDP_URL 已设置（如 http://host.docker.internal:9222）
   -> 直接连接运行在宿主机上的 Chrome，新开一个标签页抓取后关闭。
   容器内 Chromium 会被抖音识别为异常环境并降级（detail 请求拿不到响应体），
   所以容器部署推荐用这个模式。
2) 未设置 -> 自行启动本机 Chrome/Chromium（桌面端/裸机部署适用）。
"""
from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_WIN_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
_LINUX_CANDIDATES = [
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/opt/google/chrome/chrome",
]


def find_browser():
    """定位本机可用的 Chromium 系浏览器，找不到返回 None。"""
    env = os.getenv("DOUYIN_BROWSER_PATH")
    if env and os.path.exists(env):
        return env
    candidates = _WIN_CANDIDATES if sys.platform == "win32" else _LINUX_CANDIDATES
    for path in candidates:
        if os.path.exists(path):
            return path
    for name in ("chrome", "chromium", "chromium-browser", "google-chrome", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _normalize_cdp_base(base_url: str) -> str:
    """把 CDP 端点里的域名换成 IPv4。

    Chrome 有 DNS rebinding 保护：请求的 Host 既不是 IP 也不是 localhost 时，
    会直接返回 "Host header is specified and is not an IP address or localhost"。
    容器里用 host.docker.internal 访问宿主机 CDP 就会撞上这个限制，
    因此这里统一解析成 IPv4（只取 A 记录，IPv6 在 Docker Desktop 下通常不可达）。
    """
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname
    if not host:
        return base_url
    try:
        socket.inet_aton(host)
        return base_url  # 已经是 IPv4
    except OSError:
        pass
    if host == "localhost" or ":" in host:
        return base_url
    try:
        ip = socket.gethostbyname(host)
    except Exception:
        return base_url
    netloc = "%s:%d" % (ip, parsed.port) if parsed.port else ip
    return urllib.parse.urlunparse(parsed._replace(netloc=netloc))


def _http_json(url: str, method: str = "GET", timeout: float = 10.0):
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_devtools(port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    url = "http://127.0.0.1:%d/json/version" % port
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except Exception:
            time.sleep(0.4)
    return False


class _CDP:
    """极简 CDP 客户端，只用到 Network / Page 两个域。"""

    def __init__(self, ws_url: str, timeout: float = 60.0):
        import websocket  # websocket-client
        self.ws = websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)
        self._id = 0
        self.events = []

    def call(self, method: str, params=None) -> dict:
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                return msg
            self.events.append(msg)

    def pump(self, seconds: float) -> None:
        end = time.time() + seconds
        self.ws.settimeout(1.0)
        try:
            while time.time() < end:
                try:
                    msg = json.loads(self.ws.recv())
                    if "id" not in msg:
                        self.events.append(msg)
                except Exception:
                    pass
        finally:
            self.ws.settimeout(60)

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass


def _extract_detail_body(cdp: _CDP):
    """从已捕获的事件里找出 aweme/detail 响应体并解析成 dict。"""
    target_ids = []
    for e in cdp.events:
        if e.get("method") == "Network.responseReceived":
            url = (e.get("params", {}).get("response", {}) or {}).get("url", "")
            if "aweme/detail" in url:
                target_ids.append(e["params"]["requestId"])
    for rid in reversed(target_ids):  # 优先取最后一次
        res = cdp.call("Network.getResponseBody", {"requestId": rid})
        result = res.get("result") or {}
        body = result.get("body") or ""
        if result.get("base64Encoded"):
            try:
                body = base64.b64decode(body).decode("utf-8", "replace")
            except Exception:
                continue
        if not body:
            continue
        try:
            data = json.loads(body)
        except Exception:
            logger.debug("浏览器返回内容不是 JSON（前 120 字）：%s", body[:120])
            continue
        if data.get("aweme_detail"):
            return data
    return None


def _grab_with_cdp(cdp: _CDP, video_url: str, timeout: float) -> dict:
    """用给定连接跑一遍导航 + 抓取。"""
    cdp.call("Network.enable")
    cdp.call("Page.enable")
    cdp.call("Page.navigate", {"url": video_url})

    deadline = time.time() + timeout
    data = None
    while time.time() < deadline:
        cdp.pump(2.0)
        data = _extract_detail_body(cdp)
        if data:
            break
    if not data:
        raise RuntimeError("浏览器未捕获到视频详情接口响应（可能被风控或页面加载超时）")

    detail = data.get("aweme_detail") or {}
    title = detail.get("item_title") or detail.get("desc") or ""
    logger.info("浏览器抓取成功：%s", title[:60])
    return data


def _fetch_via_remote(base_url: str, video_url: str, timeout: float) -> dict:
    """连接已在运行的浏览器（DOUYIN_CDP_URL），新开标签页抓完即关。"""
    _http_json(base_url + "/json/version", timeout=8)  # 探活，失败会抛 HTTPError/URLError

    tab = _http_json(base_url + "/json/new?" + urllib.parse.quote("about:blank", safe=""), method="PUT")
    tab_id = tab.get("id")
    try:
        cdp = _CDP(tab["webSocketDebuggerUrl"])
        try:
            return _grab_with_cdp(cdp, video_url, timeout)
        finally:
            cdp.close()
    finally:
        if tab_id:
            try:
                _http_json(base_url + "/json/close/" + tab_id, timeout=5)
            except Exception:
                pass


def _fetch_via_local(video_url: str, timeout: float) -> dict:
    """自启动本机浏览器抓取。"""
    browser = find_browser()
    if not browser:
        raise RuntimeError(
            "未找到 Chrome/Chromium。请安装 Chrome，或设置 DOUYIN_BROWSER_PATH 指向浏览器，"
            "或设置 DOUYIN_CDP_URL 指向一个已开启调试端口的浏览器。"
        )

    port = _free_port()
    profile = tempfile.mkdtemp(prefix="bilinote_douyin_")
    proc = None
    cdp = None
    try:
        args = [
            browser,
            "--remote-debugging-port=%d" % port,
            "--remote-allow-origins=*",
            "--user-data-dir=" + profile,
            "--headless=new",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--mute-audio",
            "--user-agent=" + DEFAULT_UA,
            "--lang=zh-CN",
            "--window-size=1280,900",
            "about:blank",
        ]
        logger.info("启动本地浏览器抓取抖音：%s（调试端口 %d）", browser, port)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=creationflags)
        if not _wait_devtools(port, timeout=30):
            raise RuntimeError("浏览器调试端口未就绪")

        tabs = _http_json("http://127.0.0.1:%d/json" % port)
        pages = [t for t in tabs if t.get("type") == "page"]
        if not pages:
            raise RuntimeError("浏览器没有可用页面")

        cdp = _CDP(pages[0]["webSocketDebuggerUrl"])
        return _grab_with_cdp(cdp, video_url, timeout)
    finally:
        if cdp:
            cdp.close()
        if proc and proc.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                   capture_output=True, timeout=15)
                else:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            except Exception:
                pass
        shutil.rmtree(profile, ignore_errors=True)


def fetch_detail_via_browser(video_url: str, timeout: float = 60.0) -> dict:
    """用真实浏览器打开抖音视频页，抓取 detail 接口的 JSON 响应。

    :param video_url: 抖音分享短链或视频页链接
    :param timeout: 等待接口响应的最长时间（秒）
    :return: 与原 aweme/detail 接口结构一致的 dict
    :raises RuntimeError: 无可用浏览器 / 启动失败 / 超时未拿到数据
    """
    remote = (os.getenv("DOUYIN_CDP_URL") or "").strip()
    if remote:
        base = _normalize_cdp_base(remote.rstrip("/"))
        logger.info("使用宿主机浏览器抓取抖音：%s -> %s", remote, base)
        return _fetch_via_remote(base, video_url, timeout)
    return _fetch_via_local(video_url, timeout)
