import json
from pathlib import Path
from typing import Any, Dict


class AppSettingsManager:
    """通用应用设置，JSON 持久化，风格对齐 TranscriberConfigManager。

    新增设置项只需在 DEFAULTS 里加一个键：读取时会自动补齐默认值，
    写入时只接受 DEFAULTS 中已声明的键，避免脏数据落盘。
    """

    DEFAULTS: Dict[str, Any] = {
        # 笔记生成成功后，自动删除本次任务用到的视频/音频文件以节省磁盘。
        # 笔记本身（markdown / 转写 / 封面）不受影响。
        "auto_delete_media": False,
        # 可选：视频/音频的下载保存目录（容器内绝对路径）。
        # 留空表示用默认的 data 目录；填了就优先用它。
        "download_dir": "",
    }

    def __init__(self, filepath: str = "config/app_settings.json"):
        self.path = Path(filepath)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write(self, data: Dict[str, Any]):
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_settings(self) -> Dict[str, Any]:
        """返回补全默认值后的完整设置。"""
        data = dict(self.DEFAULTS)
        for key, value in self._read().items():
            if key in self.DEFAULTS:
                data[key] = value
        return data

    def update_settings(self, **kwargs) -> Dict[str, Any]:
        """只更新已声明的键；值为 None 的键会被忽略。"""
        data = self._read()
        for key, value in kwargs.items():
            if key not in self.DEFAULTS or value is None:
                continue
            if isinstance(self.DEFAULTS[key], bool):
                data[key] = bool(value)
            else:
                data[key] = value
        self._write(data)
        return self.get_settings()

    def get(self, key: str, default: Any = None) -> Any:
        return self.get_settings().get(key, default)
