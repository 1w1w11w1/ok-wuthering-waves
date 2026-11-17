# -*- coding: utf-8 -*-
r"""
GamepadInteraction —— 用 ViGEm 虚拟 Xbox360 手柄替代键鼠注入。

为什么存在：
    ok-ww 原有两条注入路径在 ACE 的取证能力面前都不成立。
    - PostMessageInteraction：只发窗口消息，GetCurrentInputMessageSource 返回
      dev=0/origin=0（IMDT_UNAVAILABLE/IMO_UNAVAILABLE），零 WM_INPUT。
    - Pynput/PyDirect/Genshin：底层 SendInput，返回 dev=1/origin=2（IMO_INJECTED），
      RawInput 报文 hDevice==NULL，LL 钩子带 LLKHF_INJECTED/LLMHF_INJECTED。
    - UIAccess + SendInput：能把 origin 抬到 1（IMO_HARDWARE），但 hDevice 仍为 NULL、
      LL 钩子 injected 位仍置 1 —— 三层硬指纹只骗过第一层。

    ViGEm 走的是内核 HID 报文：实测 RawInput 收到 hDevice 非空、
    dev_name 为 \?\HID#VID_045E&PID_028E&IG_00#...（真 VID/PID）、
    LL 钩子 flags 无 injected 位、设备枚举里存在对应节点。
    ACE-CORE 的 HID 过滤目标是 hidusb/kbdclass/mouclass/hidclass + virtualhid.sys，
    不含 xinputhid/ViGEmBus；ACE 全组件对 ViGEm/xusb/IG_00/Nefarius 零字符串命中。

用法（config.py）：
    from src.interaction.GamepadInteraction import GamepadInteraction
    'interaction': [GamepadInteraction, 'PostMessage', 'Pynput']

注意：
    * DeviceManager 只取 interaction[0]，且允许直接放类对象（DeviceManager.py:117-118）。
    * 构造签名必须是 (capture, hwnd_window)（DeviceManager.py:671-672）。
    * 手柄语义与键鼠不是一一对应，映射表见 KEY_TO_PAD / KEY_TO_PAD_FALLBACK。
"""

import ctypes
import math
import random
import time

from ok.device.interaction_methods.base import BaseInteraction
from ok.util.logger import Logger

logger = Logger.get_logger(__name__)

# ---------------------------------------------------------------------------
# 逻辑键 -> 手柄按钮
# 依据：E:\Program Files\Wuthering Waves\Wuthering Waves Game\Client\Saved\
#       Config\WindowsNoEditor\Input.ini 的 ActionMappings（169 条含 Gamepad_）
# ---------------------------------------------------------------------------
KEY_TO_PAD = {
    # 战斗
    'space': 'a',            # 跳跃 = Gamepad_FaceButton_Bottom
    'lshift': 'rb',          # 闪避 = RightShoulder
    'rshift': 'rb',
    'e': 'y',                # 技能1 / 共鸣 = Gamepad_FaceButton_Top
    'q': 'lt',               # 幻象2 / 声骸 = Gamepad_LeftTrigger
    'r': 'rt',               # 大招 / 解放 = Gamepad_RightTrigger
    'f': 'b',                # 通用交互 = Gamepad_FaceButton_Right
    'esc': 'start',          # 功能菜单 / UI返回 = Gamepad_Special_Right
    'enter': 'back',         # 聊天 / 地图 = Gamepad_Special_Left
    'm': 'back',             # 地图 = Gamepad_Special_Left
    'tab': 'dpad_left',      # 轮盘（原生是 RightShoulder，与闪避冲突，改用 DPad）
    # 切角色
    '1': 'dpad_up',          # 切换角色1 = Gamepad_DPad_Up
    '2': 'dpad_right',       # 切换角色2 = Gamepad_DPad_Right
    '3': 'dpad_down',        # 切换角色3 = Gamepad_DPad_Down
    # 移动
    'w': ('ls', 0, 1),
    's': ('ls', 0, -1),
    'a': ('ls', -1, 0),
    'd': ('ls', 1, 0),
    'up': ('ls', 0, 1),
    'down': ('ls', 0, -1),
    'left': ('ls', -1, 0),
    'right': ('ls', 1, 0),
}

# 原生没有 Gamepad_ 映射、但确实是活路径的键 —— 走 PostMessage 回退。
#   b  (背包)         config.py:140 Bag Key -> src/task/MergeEchoTask.py:26
#   t  (幻象1/工具)   config.py:135 Tool Key -> src/char/BaseChar.py:202,
#                     src/task/BaseWWTask.py:291
#   f2 (索拉指南)     config.py:139 Guidebook Key -> src/task/BaseWWTask.py:1019
#                     openF2Book()，被 9 个任务调用
# 这三个键的调用点全部在【菜单阶段】（前面都有 ensure_main），不在战斗中，
# 所以走 PostMessage 不会与手柄的战斗输入产生"同时两种输入源"的矛盾。
#   Gamepad_Special_Left 同时绑了 地图/聊天/图鉴，改 Guidebook Key 会开错面板，
#   因此不能靠改配置解决。
MENU_FALLBACK_KEYS = {'b', 't', 'f2'}

# 既无手柄映射、也不该发出去的键（修饰键 / 全仓零调用）
KEY_NO_PAD_BINDING = {'z', 'c', '4', 'alt', 'tab'}

# 鼠标按钮 -> 手柄按钮
MOUSE_TO_PAD = {
    'left': 'x',             # 攻击 / 手柄主攻击 = Gamepad_FaceButton_Left
    'right': 'rb',           # 闪避 = RightShoulder
    'middle': 'rs',          # 锁定目标 = Gamepad_RightThumbstick
    'x1': 'lb',
    'x2': 'lt',
}

_BUTTON_ALIASES = {
    'a': 'XUSB_GAMEPAD_A',
    'b': 'XUSB_GAMEPAD_B',
    'x': 'XUSB_GAMEPAD_X',
    'y': 'XUSB_GAMEPAD_Y',
    'lb': 'XUSB_GAMEPAD_LEFT_SHOULDER',
    'rb': 'XUSB_GAMEPAD_RIGHT_SHOULDER',
    'ls': 'XUSB_GAMEPAD_LEFT_THUMB',
    'rs': 'XUSB_GAMEPAD_RIGHT_THUMB',
    'start': 'XUSB_GAMEPAD_START',
    'back': 'XUSB_GAMEPAD_BACK',
    'dpad_up': 'XUSB_GAMEPAD_DPAD_UP',
    'dpad_down': 'XUSB_GAMEPAD_DPAD_DOWN',
    'dpad_left': 'XUSB_GAMEPAD_DPAD_LEFT',
    'dpad_right': 'XUSB_GAMEPAD_DPAD_RIGHT',
}

_TRIGGERS = {'lt', 'rt'}

STICK_MAX = 32767
DEADZONE = 200

# ---------------------------------------------------------------------------
# 时序抖动（对抗服务端行为特征，不是对抗 ACE）
# 现状：整仓 time.sleep(常量) 只有 3 个值，按下时长恒为 0.02s —— 操作时序接近
# 周期信号，做一次自相关就能看出来。人手按键时长接近对数正态，用 lognormal
# 乘子把「按下时长」的方差拉起来是最便宜的一步。
# ---------------------------------------------------------------------------
JITTER_SIGMA = 0.30    # lognormal sigma：0.3 时 1σ 区间约 [0.74x, 1.35x]
JITTER_LO = 0.5        # 相对下限：不低于 base 的一半
JITTER_HI = 2.0        # 相对上限：不高于 base 的两倍
JITTER_FLOOR = 0.010   # 绝对地板：别低于 10ms，否则游戏可能丢帧
JITTER_CEIL = 0.300    # 绝对天花板：别高于 300ms


class GamepadInteraction(BaseInteraction):
    """ViGEm 虚拟手柄输入层。"""

    PAD_NAME = 'Xbox360 (ViGEm)'

    def __init__(self, capture, hwnd_window=None):
        super().__init__(capture)
        self.hwnd_window = hwnd_window
        self._pad = None
        self._mods = None
        self._buttons_down = set()
        self._dirs_down = set()
        self._stick = (0, 0)
        self._rstick = (0, 0)
        self._triggers = (0, 0)
        self._dead = False
        self._pm = None          # PostMessage 回退实例（懒加载）
        self._ensure_pad()

    # -- 生命周期 ---------------------------------------------------------
    def _ensure_pad(self):
        if self._pad is not None or self._dead:
            return self._pad
        try:
            import vgamepad as vg
        except Exception as e:
            self._dead = True
            logger.error(f'vgamepad 不可用，GamepadInteraction 无法工作: {e}')
            return None
        try:
            self._mods = vg
            self._pad = vg.VX360Gamepad()
            self._pad.reset()
            self._pad.update()
            logger.info(f'{self.PAD_NAME} connected vid={self._pad.get_vid():#06x} '
                        f'pid={self._pad.get_pid():#06x}')
        except Exception as e:
            self._dead = True
            self._pad = None
            logger.error(f'ViGEmBus 连接失败（服务是否运行？）: {e}')
        return self._pad

    @property
    def connected(self):
        return self._pad is not None

    def on_run(self):
        if self._ensure_pad() is None:
            return
        if self.hwnd_window is not None:
            try:
                self.hwnd_window.bring_to_front()
            except Exception as e:
                logger.debug(f'bring_to_front failed: {e}')

    def on_destroy(self):
        self._release_all()
        if self._pad is not None:
            try:
                self._pad.reset()
                self._pad.update()
            except Exception:
                pass
        self._pad = None

    def on_off(self):
        self.on_destroy()

    def should_capture(self):
        return True

    def clickable(self):
        return True

    def activate(self, hwnd=None):
        """手柄不受窗口焦点影响（XInput 轮询），但 UE 失焦可能暂停输入处理。"""
        if self.hwnd_window is not None:
            try:
                self.hwnd_window.bring_to_front()
            except Exception:
                pass

    def deactivate(self, hwnd=None):
        self._release_all()

    # -- 底层状态推送 -----------------------------------------------------
    def _apply(self):
        if self._pad is None:
            return
        pad = self._pad
        pad.left_joystick(int(self._stick[0]), int(self._stick[1]))
        pad.right_joystick(int(self._rstick[0]), int(self._rstick[1]))
        pad.left_trigger(int(self._triggers[0]))
        pad.right_trigger(int(self._triggers[1]))
        press = getattr(pad, 'press_button')
        release = getattr(pad, 'release_button')
        for name in list(self._buttons_down):
            btn = getattr(self._mods.XUSB_BUTTON, _BUTTON_ALIASES[name])
            press(btn)
        for name in list(_BUTTON_ALIASES):
            if name in self._buttons_down:
                continue
            btn = getattr(self._mods.XUSB_BUTTON, _BUTTON_ALIASES[name])
            release(btn)
        pad.update()

    def _btn(self, name):
        return getattr(self._mods.XUSB_BUTTON, _BUTTON_ALIASES[name])

    def _press(self, name):
        if self._pad is None or name in _TRIGGERS:
            if name == 'lt':
                self._triggers = (255, self._triggers[1])
            elif name == 'rt':
                self._triggers = (self._triggers[0], 255)
            self._apply()
            return
        if name not in _BUTTON_ALIASES:
            logger.debug(f'no pad button for {name}')
            return
        self._buttons_down.add(name)
        self._pad.press_button(self._btn(name))
        self._pad.update()

    def _release(self, name):
        if self._pad is None:
            return
        if name == 'lt':
            self._triggers = (0, self._triggers[1])
            self._apply()
            return
        if name == 'rt':
            self._triggers = (self._triggers[0], 0)
            self._apply()
            return
        if name not in _BUTTON_ALIASES:
            return
        self._buttons_down.discard(name)
        self._pad.release_button(self._btn(name))
        self._pad.update()

    def _release_all(self):
        self._buttons_down.clear()
        self._dirs_down.clear()
        self._stick = (0, 0)
        self._rstick = (0, 0)
        self._triggers = (0, 0)
        if self._pad is not None:
            try:
                self._pad.reset()
                self._pad.update()
            except Exception:
                pass

    def _stick_from_dirs(self):
        """按当前按住的移动键集合合成左摇杆向量，支持 w+d 这类斜走。"""
        x = y = 0
        for k in self._dirs_down:
            t = KEY_TO_PAD.get(k)
            if not isinstance(t, tuple):
                continue
            _, dx, dy = t
            x += dx
            y += dy
        x = max(-1, min(1, x)) * STICK_MAX
        y = max(-1, min(1, y)) * STICK_MAX
        self._stick = (int(x), int(y))
        self._apply()

    def _set_stick(self, dx, dy):
        """兼容旧调用：直接给定方向写摇杆（会被下一次 _stick_from_dirs 覆盖）。"""
        self._stick = (int(dx * STICK_MAX), int(dy * STICK_MAX))
        self._apply()

    # -- PostMessage 回退（菜单/UI 专用键） -------------------------------
    def _ensure_pm(self):
        """懒加载 PostMessageInteraction，用于没有手柄映射的菜单键。"""
        if self._pm is not None:
            return self._pm
        try:
            from ok.device.interaction_methods.post_message import PostMessageInteraction
            self._pm = PostMessageInteraction(self.capture, self.hwnd_window)
        except Exception as e:
            logger.error(f'PostMessage 回退不可用: {e}')
        return self._pm

    def _post_key_down(self, key):
        pm = self._ensure_pm()
        if pm is not None:
            pm.send_key_down(key)

    def _post_key_up(self, key):
        pm = self._ensure_pm()
        if pm is not None:
            pm.send_key_up(key)

    # -- 时序抖动 ---------------------------------------------------------
    @staticmethod
    def _jitter(base):
        """把常量时长换成对数正态乘子。base<=0 时原样返回。"""
        try:
            base = float(base)
        except (TypeError, ValueError):
            return base
        if base <= 0:
            return base
        mul = random.lognormvariate(0.0, JITTER_SIGMA)
        lo = max(JITTER_FLOOR, base * JITTER_LO)
        hi = min(JITTER_CEIL, base * JITTER_HI)
        if hi <= lo:
            return base
        return min(hi, max(lo, base * mul))

    # -- 键语义 -----------------------------------------------------------
    def send_key_down(self, key):
        k = str(key).lower()
        target = KEY_TO_PAD.get(k)
        if target is None and k in MENU_FALLBACK_KEYS:
            self._post_key_down(k)          # 菜单键：不依赖手柄是否可用
            return
        if self._pad is None:
            return
        if target is None:
            if k not in KEY_NO_PAD_BINDING:
                logger.debug(f'GamepadInteraction: 未映射的键 {k}（忽略）')
            return
        if isinstance(target, tuple):
            self._dirs_down.add(k)
            self._stick_from_dirs()
        else:
            self._press(target)

    def send_key_up(self, key):
        k = str(key).lower()
        target = KEY_TO_PAD.get(k)
        if target is None and k in MENU_FALLBACK_KEYS:
            self._post_key_up(k)
            return
        if self._pad is None:
            return
        if target is None:
            return
        if isinstance(target, tuple):
            self._dirs_down.discard(k)
            self._stick_from_dirs()
        else:
            self._release(target)

    def send_key(self, key, down_time=0.02):
        super().send_key(key, down_time)
        if self._pad is None and str(key).lower() not in MENU_FALLBACK_KEYS:
            return
        self.send_key_down(key)
        time.sleep(self._jitter(max(0.01, down_time)))
        self.send_key_up(key)

    def back(self, *args, **kwargs):
        self.send_key('esc')

    # -- 鼠标语义 ---------------------------------------------------------
    def click(self, x=-1, y=-1, move_back=False, name=None, down_time=0.05,
              move=True, key='left', **kwargs):
        super().click(x, y, move_back=move_back, name=name, move=move, down_time=down_time)
        if self._pad is None:
            return
        pad_btn = MOUSE_TO_PAD.get(str(key).lower(), 'x')
        if x is not None and y is not None and x > 0 and y > 0 and move:
            self._aim(x, y)
        self._press(pad_btn)
        time.sleep(self._jitter(max(0.01, down_time)))
        self._release(pad_btn)
        if move_back and self.hwnd_window is not None:
            try:
                cx = self.hwnd_window.width // 2
                cy = self.hwnd_window.height // 2
                self._aim(cx, cy)
            except Exception:
                pass

    def mouse_down(self, x=-1, y=-1, name=None, key='left'):
        if self._pad is None:
            return
        if x is not None and y is not None and x > 0 and y > 0:
            self._aim(x, y)
        self._press(MOUSE_TO_PAD.get(str(key).lower(), 'x'))

    def mouse_up(self, name=None, key='left'):
        self._release(MOUSE_TO_PAD.get(str(key).lower(), 'x'))

    def _aim(self, x, y, gain=1.0, pulse=0.06):
        """把屏幕点 (x,y) 往画面中心拉：右摇杆方向脉冲。"""
        if self._pad is None or self.hwnd_window is None:
            return
        try:
            cx = self.hwnd_window.width / 2
            cy = self.hwnd_window.height / 2
        except Exception:
            return
        dx = (x - cx) / max(1.0, cx)
        dy = (y - cy) / max(1.0, cy)
        if abs(dx) < 0.02 and abs(dy) < 0.02:
            return
        rx = int(max(-1.0, min(1.0, dx)) * STICK_MAX * gain)
        ry = int(max(-1.0, min(1.0, -dy)) * STICK_MAX * gain)
        self._rstick = (rx, ry)
        self._apply()
        time.sleep(self._jitter(pulse))
        self._rstick = (0, 0)
        self._apply()

    def move(self, x, y, down_btn=0):
        self._aim(x, y)

    def swipe(self, from_x, from_y, to_x, to_y, duration=300, settle_time=0, **kwargs):
        """src 侧零调用，保留最小可用实现：右摇杆扫视。"""
        if self._pad is None:
            return
        steps = max(2, int(duration / 20))
        dx = (to_x - from_x) / max(1.0, self.hwnd_window.width if self.hwnd_window else 1)
        dy = (to_y - from_y) / max(1.0, self.hwnd_window.height if self.hwnd_window else 1)
        for _ in range(steps):
            self._rstick = (int(max(-1.0, min(1.0, dx)) * STICK_MAX),
                            int(max(-1.0, min(1.0, -dy)) * STICK_MAX))
            self._apply()
            time.sleep(self._jitter(0.02))
        self._rstick = (0, 0)
        self._apply()
        if settle_time:
            time.sleep(self._jitter(settle_time))

    def scroll(self, x, y, scroll_amount, **kwargs):
        """手柄无滚动语义：转成 DPad 上下脉冲（UI 轴向滚动）。"""
        if self._pad is None:
            return
        btn = 'dpad_up' if scroll_amount > 0 else 'dpad_down'
        for _ in range(max(1, abs(int(scroll_amount)))):
            self._press(btn)
            time.sleep(self._jitter(0.05))
            self._release(btn)
            time.sleep(self._jitter(0.02))

    def input_text(self, text, **kwargs):
        """
        手柄没有文字输入通道（F2 图鉴搜索框需要打字）。
        回退到 PostMessage WM_CHAR 直送目标窗口 —— 该路径不参与战斗输入，
        ACE 对 WM_CHAR 只能判到 dev=0/origin=0，与正常文本输入无法区分。
        """
        if not text:
            return
        hwnd = None
        if self.hwnd_window is not None:
            hwnd = getattr(self.hwnd_window, 'top_hwnd', None) or getattr(self.hwnd_window, 'hwnd', None)
        if not hwnd:
            logger.error('input_text: 没有可用 hwnd')
            return
        user32 = ctypes.windll.user32
        for ch in str(text):
            user32.PostMessageW(hwnd, 0x0102, ord(ch), 0)
            time.sleep(self._jitter(0.02))

    def __repr__(self):
        return f'<GamepadInteraction connected={self.connected}>'
