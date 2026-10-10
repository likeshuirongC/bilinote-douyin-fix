import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

# get_data_dir() 被各下载器频繁调用，不能每次都去读设置文件；
# 缓存几秒，设置页保存时会主动失效。
_custom_dir_cache = {"value": None, "checked_at": 0.0}
_CUSTOM_DIR_TTL = 5.0


def invalidate_download_dir_cache():
    """设置更新后立即失效缓存，不必等 TTL 过期。"""
    _custom_dir_cache["value"] = None
    _custom_dir_cache["checked_at"] = 0.0


def get_custom_download_dir():
    """返回设置里指定的下载目录；未配置 / 不可用时返回 None。

    只认绝对路径，且必须能创建、可写 —— 否则静默回退到默认目录，
    免得一个笔误让所有下载都失败。
    """
    now = time.time()
    if now - _custom_dir_cache["checked_at"] < _CUSTOM_DIR_TTL:
        return _custom_dir_cache["value"]

    value = None
    try:
        # 延迟导入：path_helper 在 utils 层，直接顶层导入 services 会形成循环依赖
        from app.services.app_settings_manager import AppSettingsManager

        raw = str(AppSettingsManager().get("download_dir") or "").strip()
        if raw and os.path.isabs(raw):
            os.makedirs(raw, exist_ok=True)
            if os.path.isdir(raw) and os.access(raw, os.W_OK):
                value = os.path.abspath(raw)
    except Exception:
        value = None

    _custom_dir_cache["value"] = value
    _custom_dir_cache["checked_at"] = now
    return value


def get_data_dir():
    # "可选文件下载地址"：设置里填了有效目录就优先用它
    custom = get_custom_download_dir()
    if custom:
        return custom

    if getattr(sys, 'frozen', False):

        base_dir = os.path.dirname(sys.executable)
    else:

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))

    data_path = os.path.join(base_dir, "data")
    os.makedirs(data_path, exist_ok=True)
    return data_path


def get_model_dir(subdir: str = "whisper") -> str:
    # 判断是否为打包状态（PyInstaller）
    if getattr(sys, 'frozen', False):
        # exe 执行，放在 APPDATA 或 ~/.cache 下
        base_dir = os.path.join(os.getenv("APPDATA") or str(Path.home()), "BiliNote", "models")
    else:
        # 开发时，相对项目根目录
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models"))

    path = os.path.join(base_dir, subdir)
    os.makedirs(path, exist_ok=True)
    return path


def get_app_dir(subdir: str = "") -> str:
    """
    返回一个稳定的可写目录：
    - 开发时：使用项目 data 目录
    - 打包后：使用 exe 所在目录
    """
    if getattr(sys, 'frozen', False):
        # 打包后运行：使用 main.exe 所在目录
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发模式：使用项目的 /data 目录
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))

    full_path = os.path.join(base_dir, subdir)
    os.makedirs(full_path, exist_ok=True)
    return full_path