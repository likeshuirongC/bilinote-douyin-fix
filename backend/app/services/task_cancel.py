# -*- coding: utf-8 -*-
"""任务取消登记表（协作式取消）。

FastAPI 的 BackgroundTasks 一旦提交就没法取消，所以这里维护一张
"task_id -> Event" 的表：任务执行期间登记自己，在几个关键阶段检查是否被取消；
前端点"删除/取消"时调 cancel()，任务会在下一个检查点主动退出。

限制（要如实说明）：这是**协作式**取消，只能在检查点生效 ——
没法打断正在进行中的单次网络请求（比如一次正在跑的 LLM 调用）。
所以最坏情况是"刚要取消时正好发出了一次请求"，之后才会退出。
"""
import threading
from typing import Dict

_lock = threading.Lock()
_events: Dict[str, threading.Event] = {}


def register(task_id: str) -> threading.Event:
    """任务开始时登记，返回它自己的 Event。"""
    ev = threading.Event()
    with _lock:
        _events[task_id] = ev
    return ev


def unregister(task_id: str) -> None:
    """任务结束时清理。"""
    with _lock:
        _events.pop(task_id, None)


def cancel(task_id: str) -> bool:
    """标记取消；返回该任务是否仍在执行（登记过）。"""
    with _lock:
        ev = _events.get(task_id)
    if ev is None:
        return False
    ev.set()
    return True


def is_cancelled(task_id: str) -> bool:
    with _lock:
        ev = _events.get(task_id)
    return bool(ev is not None and ev.is_set())


def ensure_not_cancelled(task_id: str) -> None:
    """检查点调用：已取消则抛出 TaskCancelled。"""
    if task_id and is_cancelled(task_id):
        raise TaskCancelled(task_id)


class TaskCancelled(Exception):
    """任务被用户取消（区别于失败）。"""

    def __init__(self, task_id: str = ""):
        super().__init__("任务已取消: %s" % task_id)
        self.task_id = task_id
