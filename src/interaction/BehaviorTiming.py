# -*- coding: utf-8 -*-
"""
行为层时序扰动 —— 对抗服务端行为特征（不是对抗 ACE）。

为什么存在：
    客户端 ACE 的检测面已经用 ViGEm 手柄通道绕开了（见 GamepadInteraction）。
    但社区实证（issue #1840「换了 pynput 版照样被封」）指向服务端行为判定。
    而本仓库的时序特征极其干净：
        random.(uniform|randint|random|choice) 全仓 0 命中
        time.sleep(常量) 只有 3 个值（0.02 / 0.05 / 0.1），共 8 处
    这意味着操作时间轴接近周期信号，一次自相关就能看出机器特征。

本模块提供两层，都可单独关闭：
    1. jitter_seconds(sec)        —— 把常量等待换成对数正态抖动
    2. BreakScheduler             —— 每 40~70 分钟插一次 3~12 分钟完全空闲

用法（BaseWWTask）：
    from src.interaction.BehaviorTiming import jitter_seconds, BreakScheduler
    self._break_scheduler = BreakScheduler()
    def sleep(self, timeout):
        ...
        if self._break_scheduler.due():
            self._break_scheduler.take_break(lambda s: super().sleep(s))
        return super().sleep(jitter_seconds(timeout))
"""

import random
import time

# 对数正态 sigma。0.15 -> 1σ 区间约 [0.86x, 1.16x]，对动画等待类的 sleep 足够安全。
SLEEP_JITTER_SIGMA = 0.15

# 长休息参数（分钟）
BREAK_EVERY_MIN = 40.0
BREAK_EVERY_MAX = 70.0
BREAK_LEN_MIN = 3.0
BREAK_LEN_MAX = 12.0


def jitter_seconds(sec, sigma=SLEEP_JITTER_SIGMA, lo=0.75, hi=1.35):
    """
    把常量等待时长换成对数正态抖动。

    :param sec: 原始等待秒数。<=0 时原样返回（sleep(0) 语义要保持）。
    :param sigma: 对数正态 sigma。
    :param lo/hi: 相对夹逼上下限，防止极端采样把等待拉得太离谱。
    :return: 抖动后的秒数。
    """
    try:
        sec = float(sec)
    except (TypeError, ValueError):
        return sec
    if sec <= 0:
        return sec
    mul = random.lognormvariate(0.0, float(sigma))
    return min(sec * float(hi), max(sec * float(lo), sec * mul))


class BreakScheduler:
    """
    长休息调度器：每隔 [BREAK_EVERY_MIN, BREAK_EVERY_MAX] 分钟安排一次
    [BREAK_LEN_MIN, BREAK_LEN_MAX] 分钟的完全空闲。

    为什么需要：连续在线 8 小时且操作周期恒定，是服务端最容易看到的特征；
    人类不会这样。插入长间隔后「在线时长 / 有效操作时长」的比值回到人类区间。
    """

    def __init__(self, every=(BREAK_EVERY_MIN, BREAK_EVERY_MAX),
                 length=(BREAK_LEN_MIN, BREAK_LEN_MAX),
                 clock=time.monotonic):
        self.every = every
        self.length = length
        self._clock = clock
        self._next_break_at = clock() + self._sample(self.every) * 60.0
        self.breaks_taken = 0
        self.total_break_seconds = 0.0

    @staticmethod
    def _sample(pair):
        lo, hi = float(pair[0]), float(pair[1])
        if hi <= lo:
            return lo
        return random.uniform(lo, hi)

    def due(self):
        """是否到了该休息的时间点。"""
        return self._clock() >= self._next_break_at

    def next_break_in(self):
        """距离下次休息还有多少秒（负数表示已逾期）。"""
        return self._next_break_at - self._clock()

    def schedule_next(self):
        """安排下一次休息。"""
        self._next_break_at = self._clock() + self._sample(self.every) * 60.0

    def break_length(self):
        """本次休息的秒数。"""
        return self._sample(self.length) * 60.0

    def take_break(self, sleeper):
        """
        执行一次长休息。sleeper 是一个接受秒数的函数（通常是 task.sleep）。

        :return: 实际休息的秒数。
        """
        seconds = self.break_length()
        remaining = seconds
        step = 30.0
        while remaining > 0:
            chunk = min(step, remaining)
            sleeper(chunk)
            remaining -= chunk
        self.breaks_taken += 1
        self.total_break_seconds += seconds
        self.schedule_next()
        return seconds

    def __repr__(self):
        return (f'<BreakScheduler next_in={self.next_break_in() / 60.0:.1f}min '
                f'taken={self.breaks_taken}>')
