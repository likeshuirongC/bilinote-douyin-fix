# -*- coding: utf-8 -*-
"""从用户粘贴的分享文本里提取视频链接。

手机端抖音 / 快手 / B站 等分享出来的是整段文案，形如：

    6.41 K@w.Sl :6pm 03/04 uSL:/ 标题正文... # 话题
    https://v.douyin.com/xxxx/ 复制此链接，打开抖音搜索，直接观看视频！

真正的链接夹在中间。这里统一抽出第一个 http(s) 链接，
避免每个下载器各写各的正则、也避免校验先一步把整段文本判成非法。
"""
import re

# 只允许 URL 里常见的字符：中文、空格、全角标点都不在集合内，天然成为终止符
_URL_PATTERN = r"https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+"
_URL_RE = re.compile(_URL_PATTERN, re.IGNORECASE)
_LEADING_RE = re.compile(r"https?://\S+", re.IGNORECASE)
# 链接尾部被文本带上的标点
_TRAILING = "，。、！？；：）】》」』\"'”’,.;:!?)>]}"


def extract_first_url(text) -> str:
    """返回文本中的第一个 http(s) 链接；找不到链接时原样返回。"""
    if text is None:
        return text
    s = str(text).strip()
    if not s:
        return s
    if s.lower().startswith(("http://", "https://")):
        m = _LEADING_RE.match(s)
        if not m:
            return s
    else:
        m = _URL_RE.search(s)
        if not m:
            return s
    return m.group(0).rstrip(_TRAILING)
